"""Station acceptance checks; each e-number is one learner exercise."""
from collections import deque
from pathlib import Path
from time import perf_counter

import pytest

from starter.review3 import (
    FakeTransport,
    ReplyReader,
    SignalGenerator,
    run_with_output,
    load_hold_channels,
    peak_backlog,
    split_replies,
)


class RecordingTransport:
    """Independent fake so driver checks do not depend on E1."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []
        self.reply = " \tLAB,SG1,42,1.0\r\n"
        self.failure: BaseException | None = None
        self.fail_on = ""

    def write(self, command: str) -> None:
        self.events.append(("write", command))
        if command == self.fail_on and self.failure is not None:
            raise self.failure

    def query(self, command: str) -> str:
        self.events.append(("query", command))
        if self.failure is not None:
            raise self.failure
        return self.reply


@pytest.fixture
def transport() -> RecordingTransport:
    return RecordingTransport()


class OutputSpy:
    """Record output attempts, including ones that fail."""

    def __init__(self) -> None:
        self.events: list[bool | str] = []
        self.failures: dict[bool, BaseException] = {}

    def output(self, on: bool) -> None:
        self.events.append(on)
        if on in self.failures:
            raise self.failures[on]


@pytest.fixture
def output_spy() -> OutputSpy:
    return OutputSpy()


class ChunkSource:
    """Never blocks; unexpected extra reads fail immediately."""

    def __init__(self, chunks: list[bytes | BaseException]) -> None:
        self.chunks = deque(chunks)
        self.sizes: list[int] = []

    def __call__(self, size: int) -> bytes:
        self.sizes.append(size)
        assert self.chunks, "reader made an unexpected extra receive call"
        chunk = self.chunks.popleft()
        if isinstance(chunk, BaseException):
            raise chunk
        assert len(chunk) <= size, "test source must respect the requested receive size"
        return chunk


def test_e1_write_query_history_and_repeated_reply() -> None:
    fake = FakeTransport({"*IDN?": " LAB,SG1,42,1.0\n"})
    assert fake.writes == [], "a new connection must have no command history"
    fake.write("FUNC SIN")
    assert fake.query("*IDN?") == " LAB,SG1,42,1.0\n", "the fake must preserve reply text"
    assert fake.query("*IDN?") == " LAB,SG1,42,1.0\n", "scripted replies are reusable"
    assert fake.writes == ["FUNC SIN", "*IDN?", "*IDN?"], "writes and queries share one ordered history"


def test_e1_reply_copy_and_independent_histories() -> None:
    script = {"OUTP?": "0"}
    first = FakeTransport(script)
    second = FakeTransport(script)
    script["OUTP?"] = "1"
    script["NEW?"] = "new"
    assert first.query("OUTP?") == "0", "copy the reply script at construction"
    assert second.writes == [], "history must belong to one connection"
    with pytest.raises(KeyError):
        first.query("NEW?")
    assert first.writes == ["OUTP?", "NEW?"], "failed queries are recorded too"


def test_e1_unknown_query_is_recorded_without_breaking_known_query() -> None:
    fake = FakeTransport({"OUTP?": "0"})
    with pytest.raises(KeyError):
        fake.query("MISSING?")
    assert fake.query("OUTP?") == "0"
    assert fake.writes == ["MISSING?", "OUTP?"], "do not drop unsuccessful query attempts"


def test_e2_constructor_and_identification(transport: RecordingTransport) -> None:
    generator = SignalGenerator(transport)
    assert transport.events == [], "constructing a driver must not change the instrument"
    assert generator.idn() == "LAB,SG1,42,1.0", "strip only the reply's outer whitespace"
    assert transport.events == [("query", "*IDN?")], "identity must use query, not write"


@pytest.mark.parametrize(
    ("frequency", "amplitude", "commands"),
    [
        (1250.25, 1.25, ["FUNC SIN", "FREQ 1250.2", "VOLT 1.250"]),
        (1.0, 0.0, ["FUNC SIN", "FREQ 1.0", "VOLT 0.000"]),
        (1_000_000.0, 5.0, ["FUNC SIN", "FREQ 1000000.0", "VOLT 5.000"]),
        (120.06, 0.1236, ["FUNC SIN", "FREQ 120.1", "VOLT 0.124"]),
    ],
)
def test_e2_configure_exact_sequence(
    transport: RecordingTransport, frequency: float, amplitude: float, commands: list[str]
) -> None:
    generator = SignalGenerator(transport)
    assert generator.configure(frequency, amplitude) is None
    assert transport.events == [("write", command) for command in commands], "check order, precision, and no automatic output-on"


@pytest.mark.parametrize(
    ("frequency", "amplitude"),
    [
        (0.9999, 1.0), (1_000_000.01, 1.0), (-1.0, 1.0),
        (float("nan"), 1.0), (float("inf"), 1.0), (float("-inf"), 1.0),
        (100.0, -0.00001), (100.0, 5.00001), (100.0, float("nan")),
        (100.0, float("inf")), (100.0, float("-inf")),
    ],
)
def test_e2_reject_invalid_before_any_write(
    transport: RecordingTransport, frequency: float, amplitude: float
) -> None:
    generator = SignalGenerator(transport)
    with pytest.raises(ValueError):
        generator.configure(frequency, amplitude)
    assert transport.events == [], f"unsafe settings {(frequency, amplitude)} must send no commands"


def test_e2_output_switch(transport: RecordingTransport) -> None:
    generator = SignalGenerator(transport)
    assert generator.output(True) is None
    assert generator.output(False) is None
    assert transport.events == [("write", "OUTP ON"), ("write", "OUTP OFF")]


def test_e2_stop_configuration_on_transport_error(transport: RecordingTransport) -> None:
    generator = SignalGenerator(transport)
    failure = OSError("connection lost while setting frequency")
    transport.failure = failure
    transport.fail_on = "FREQ 100.0"
    with pytest.raises(OSError) as caught:
        generator.configure(100.0, 1.0)
    assert caught.value is failure, "preserve the transport failure"
    assert transport.events == [("write", "FUNC SIN"), ("write", "FREQ 100.0")], "do not continue after a failed command"


def test_e2_identity_transport_error_propagates(transport: RecordingTransport) -> None:
    generator = SignalGenerator(transport)
    failure = TimeoutError("identity timed out")
    transport.failure = failure
    with pytest.raises(TimeoutError) as caught:
        generator.idn()
    assert caught.value is failure
    assert transport.events == [("query", "*IDN?")], "do not retry a failed query"


@pytest.mark.parametrize("value", [0.82, -1.0, float("nan")])
def test_e3_measure_and_cleanup_in_order(output_spy: OutputSpy, value: float) -> None:
    def measure() -> float:
        output_spy.events.append("measure")
        return value

    result = run_with_output(output_spy, measure)
    assert result is value, "return the measurement unchanged, including NaN"
    assert output_spy.events == [True, "measure", False], "enable before measurement and disable afterward"


def test_e3_failed_enable_still_attempts_off(output_spy: OutputSpy) -> None:
    failure = OSError("enable acknowledgement lost")
    output_spy.failures[True] = failure

    def measure() -> float:
        pytest.fail("do not measure when enabling failed")

    with pytest.raises(OSError) as caught:
        run_with_output(output_spy, measure)
    assert caught.value is failure
    assert output_spy.events == [True, False], "enable might have reached hardware before its error"


@pytest.mark.parametrize("error_type", [TimeoutError, ValueError, KeyboardInterrupt])
def test_e3_measurement_failure_is_preserved(
    output_spy: OutputSpy, error_type: type[BaseException]
) -> None:
    failure = error_type("measurement interrupted")

    def measure() -> float:
        output_spy.events.append("measure")
        raise failure

    with pytest.raises(error_type) as caught:
        run_with_output(output_spy, measure)
    assert caught.value is failure, "do not replace the measurement exception"
    assert output_spy.events == [True, "measure", False]


def test_e3_cleanup_only_failure_propagates(output_spy: OutputSpy) -> None:
    failure = OSError("output-off failed")
    output_spy.failures[False] = failure
    with pytest.raises(OSError) as caught:
        run_with_output(output_spy, lambda: 0.82)
    assert caught.value is failure, "a cleanup-only failure must reach the operator"
    assert output_spy.events == [True, False], "attempt cleanup once, without retries"


@pytest.mark.parametrize("stage", ["enable", "measure"])
@pytest.mark.parametrize("cleanup_type", [OSError, KeyboardInterrupt])
def test_e3_dual_failure_keeps_original(
    output_spy: OutputSpy, stage: str, cleanup_type: type[BaseException]
) -> None:
    original = TimeoutError("original station failure")
    output_spy.failures[False] = cleanup_type("cleanup failed too")
    if stage == "enable":
        output_spy.failures[True] = original

    def measure() -> float:
        output_spy.events.append("measure")
        raise original

    with pytest.raises(TimeoutError) as caught:
        run_with_output(output_spy, measure)
    assert caught.value is original, "cleanup must not hide the cause of the failed step"
    expected = [True, False] if stage == "enable" else [True, "measure", False]
    assert output_spy.events == expected, "cleanup is attempted exactly once"


@pytest.mark.parametrize(
    ("buffer", "chunk", "expected"),
    [
        (b"12", b".5\r\nREADY\npar", (["12.5", "READY"], b"par")),
        (b"", b"\n\r\nOK\n", (["", "", "OK"], b"")),
        (b"", b"", ([], b"")),
        (b"tail", b"", ([], b"tail")),
        (b"", b"OK\n\xff", (["OK"], b"\xff")),
    ],
)
def test_e4_complete_lines_and_empty_inputs(
    buffer: bytes, chunk: bytes, expected: tuple[list[str], bytes]
) -> None:
    assert split_replies(buffer, chunk) == expected, "return complete text separately from unfinished bytes"


def test_e4_cr_and_lf_can_arrive_separately() -> None:
    replies, tail = split_replies(b"", b"12.5\r")
    assert (replies, tail) == ([], b"12.5\r"), "do not decode or trim unfinished bytes"
    assert split_replies(tail, b"\n") == (["12.5"], b"")


def test_e4_every_split_and_single_byte_chunks() -> None:
    wire = b"1.0\r\nREADY\n\nend"
    expected = (["1.0", "READY", ""], b"end")
    for cut in range(len(wire) + 1):
        first, tail = split_replies(b"", wire[:cut])
        second, tail = split_replies(tail, wire[cut:])
        assert (first + second, tail) == expected, f"reply boundary split at byte {cut} lost data"
    all_replies: list[str] = []
    tail = b""
    for byte in wire:
        replies, tail = split_replies(tail, bytes([byte]))
        all_replies.extend(replies)
    assert (all_replies, tail) == expected, "one-byte receives must work too"


def test_e4_keep_spaces_and_remove_only_one_terminal_cr() -> None:
    assert split_replies(b"", b"  OK \t\r\nA\rB\nX\r\r\n") == (
        ["  OK \t", "A\rB", "X\r"], b""
    ), "only LF and its immediately preceding single CR are framing bytes"


def test_e4_non_ascii_complete_line_rejected_but_tail_retained() -> None:
    replies, tail = split_replies(b"", b"\xff")
    assert replies == [] and tail == b"\xff", "decode only complete lines"
    with pytest.raises(ValueError) as caught:
        split_replies(tail, b"\n")
    assert not isinstance(caught.value, UnicodeDecodeError), "translate decoding errors into ValueError"
    with pytest.raises(ValueError):
        split_replies(b"", b"OK\n\xff\n")


def test_e5_fragmented_coalesced_and_empty_replies() -> None:
    source = ChunkSource([b"1", b".0\r", b"\n2.0\n\npar", b"t\n"])
    reader = ReplyReader(source)
    assert source.sizes == [], "construction must not receive anything"
    assert reader.read() == "1.0"
    assert reader.read() == "2.0"
    assert reader.read() == "", "an empty line is a valid reply"
    assert source.sizes == [1024] * 3, "queued replies must not trigger extra receives"
    assert reader.read() == "part", "retain the partial line after complete replies"
    assert source.sizes == [1024] * 4
    other = ReplyReader(ChunkSource([b"separate\n"]))
    assert other.read() == "separate", "reader instances must not share pending bytes"


def test_e5_budget_boundary_reset_and_preserved_partial_bytes() -> None:
    source = ChunkSource([b"1", b"2", b"3", b"\n", b"A", b"\n"])
    reader = ReplyReader(source, max_reads=2)
    with pytest.raises(TimeoutError):
        reader.read()
    assert source.sizes == [1024, 1024], "stop at the per-read receive budget"
    assert reader.read() == "123", "keep pre-timeout bytes and allow completion on the last call"
    assert reader.read() == "A", "the receive budget resets for each reply"
    assert source.sizes == [1024] * 6
    default_source = ChunkSource([b"x"] * 20 + [b"\n"])
    default_reader = ReplyReader(default_source)
    with pytest.raises(TimeoutError):
        default_reader.read()
    assert len(default_source.sizes) == 20, "the default receive budget is 20"
    assert default_reader.read() == "x" * 20


@pytest.mark.parametrize("chunks", [[b""], [b"partial", b""]])
def test_e5_connection_closure_without_full_reply(chunks: list[bytes]) -> None:
    source = ChunkSource(list(chunks))
    reader = ReplyReader(source)
    with pytest.raises(ConnectionError):
        reader.read()
    assert len(source.sizes) == len(chunks), "closure must stop reads immediately"


@pytest.mark.parametrize("error_type", [TimeoutError, OSError])
def test_e5_receive_error_propagates_and_preserves_partial_bytes(
    error_type: type[Exception],
) -> None:
    failure = error_type("transport receive failed")
    source = ChunkSource([b"par", failure, b"t\n"])
    reader = ReplyReader(source)
    with pytest.raises(error_type) as caught:
        reader.read()
    assert caught.value is failure, "propagate the receive exception unchanged"
    assert len(source.sizes) == 2, "do not retry a receive exception within the same read"
    assert reader.read() == "part", "preserve bytes collected before the receive error"


@pytest.mark.parametrize("budget", [0, -1, -20])
def test_e5_invalid_receive_budget(budget: int) -> None:
    source = ChunkSource([b"unused\n"])
    with pytest.raises(ValueError):
        ReplyReader(source, max_reads=budget)
    assert source.sizes == [], "invalid reader settings must not consume bytes"


def test_e5_malformed_complete_reply_is_an_error() -> None:
    source = ChunkSource([b"bad\xff", b"\n"])
    reader = ReplyReader(source)
    with pytest.raises(ValueError) as caught:
        reader.read()
    assert not isinstance(caught.value, UnicodeDecodeError), "use E4's public error type"
    assert source.sizes == [1024, 1024], "non-ASCII partial bytes become invalid once terminated"


@pytest.mark.parametrize("as_string", [False, True])
def test_e6_csv_holds_preserve_names_and_ignore_run(tmp_path: Path, as_string: bool) -> None:
    path = tmp_path / "holds.csv"
    path.write_text(
        'channel,action\nBUS_V,HOLD\nTEMP_C,RUN\n"J2,pin 4",HOLD\n'
        'BUS_V,RUN\nBUS_V,HOLD\n bus_v ,HOLD\nbus_v,RUN\n温度,HOLD\n',
        encoding="utf-8",
    )
    argument: str | Path = str(path) if as_string else path
    assert load_hold_channels(argument) == {"BUS_V", "J2,pin 4", " bus_v ", "温度"}, (
        "hold wins over RUN; preserve quoted commas, Unicode, spaces, and case"
    )
    assert path.read_text(encoding="utf-8").startswith("channel,action"), "do not rewrite the hold file"
    path.unlink()  # Windows also verifies that the input file was closed.


@pytest.mark.parametrize("rows", ["", "\n", "A,RUN\nB,RUN\n"])
def test_e6_no_holds(tmp_path: Path, rows: str) -> None:
    path = tmp_path / "holds.csv"
    path.write_text("channel,action\n" + rows, encoding="utf-8")
    assert load_hold_channels(path) == set(), "no HOLD records means an empty set"


def test_e6_blank_lines_and_crlf(tmp_path: Path) -> None:
    path = tmp_path / "holds.csv"
    path.write_bytes(b"channel,action\r\n\r\nA,HOLD\r\n\r\nB,RUN\r\n")
    assert load_hold_channels(path) == {"A"}, "CSV must handle blank lines and Windows line endings"


def test_e6_missing_file_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_hold_channels(tmp_path / "missing.csv")


@pytest.mark.parametrize(
    ("events", "expected"),
    [
        ([], 0),
        (["SEND"], 1),
        (["SEND", "SEND", "SEND"], 3),
        (["SEND", "SEND", "REPLY", "SEND", "REPLY"], 2),
        (["SEND", "REPLY", "SEND", "REPLY"], 1),
        (["SEND", "SEND", "REPLY", "REPLY", "SEND", "SEND", "SEND", "REPLY"], 3),
    ],
)
def test_e7_peak_and_unfinished_commands(events: list[str], expected: int) -> None:
    before = events.copy()
    assert peak_backlog(events) == expected, f"wrong peak for {events}"
    assert events == before, "leave the recorded events unchanged"


@pytest.mark.parametrize("events", [["REPLY"], ["SEND", "REPLY", "REPLY"], ["REPLY", "SEND"]])
def test_e7_reject_unmatched_replies(events: list[str]) -> None:
    with pytest.raises(ValueError):
        peak_backlog(events)


def test_e7_calls_keep_independent_counts() -> None:
    assert peak_backlog(["SEND", "SEND"]) == 2
    assert peak_backlog([]) == 0, "each run starts without pending commands"
    with pytest.raises(ValueError):
        peak_backlog(["REPLY"])


def test_e7_fast_enough() -> None:
    events = ["SEND"] * 200_000 + ["REPLY"] * 200_000
    started = perf_counter()
    result = peak_backlog(events)
    elapsed = perf_counter() - started
    assert result == 200_000, "all sends precede replies in this run"
    assert elapsed <= 2.0, f"use a single pass with counters; took {elapsed:.3f}s"
