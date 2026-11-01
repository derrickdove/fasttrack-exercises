import pytest

from starter.scpi import build, decode_reply, encode_command, is_query, short_form, safe_power_up


@pytest.mark.parametrize("cmd, expected", [
    ("VOLT 5", b"VOLT 5\n"),
    ("*IDN?", b"*IDN?\n"),
    ("", b"\n"),
    (" OUTP ON ", b" OUTP ON \n"),
])
def test_e1_ascii_command(cmd: str, expected: bytes) -> None:
    got = encode_command(cmd)
    assert isinstance(got, bytes), "the instrument connection needs bytes"
    assert got == expected, f"command {cmd!r}: expected {expected!r}, got {got!r}"


@pytest.mark.parametrize("cmd, term, expected", [
    ("OUTP OFF\n", "\n", b"OUTP OFF\n"),
    ("OUTP OFF\n\n\n", "\n", b"OUTP OFF\n"),
    ("*IDN?\r\n\r\n", "\r\n", b"*IDN?\r\n"),
    ("READ?", "\r\n", b"READ?\r\n"),
    ("READ?;END;END", ";END", b"READ?;END"),
    ("", "\r\n", b"\r\n"),
])
def test_e1_exactly_one_terminator(cmd: str, term: str, expected: bytes) -> None:
    got = encode_command(cmd, term)
    assert got == expected, f"normalize complete {term!r} endings: got {got!r}"


def test_e1_preserves_message_body() -> None:
    got = encode_command("DISP:TEXT \"line\"\nNEXT\r", "\r\n")
    assert got == b'DISP:TEXT "line"\nNEXT\r\r\n', "preserve internal text and partial endings"


@pytest.mark.parametrize("cmd, term", [("VOLT \u00b5", "\n"), ("OUTP ON", "\u00e9"), ("\u00e9", "\u00e9")])
def test_e1_rejects_non_ascii(cmd: str, term: str) -> None:
    with pytest.raises(ValueError) as caught:
        encode_command(cmd, term)
    assert type(caught.value) is ValueError, "translate encoding failure into plain ValueError"


def test_e1_rejects_empty_terminator() -> None:
    with pytest.raises(ValueError):
        encode_command("VOLT 5", "")


@pytest.mark.parametrize("data, expected", [
    (b"  +5.020 \r\n", "+5.020"),
    (b"-100, bad command", "-100, bad command"),
    (b"  CH1  READY\t", "CH1  READY"),
    (b"", ""),
    (b" \t\n\n", ""),
])
def test_e2_ascii_reply(data: bytes, expected: str) -> None:
    got = decode_reply(data)
    assert isinstance(got, str), "reply checking needs text"
    assert got == expected, f"reply {data!r}: expected {expected!r}, got {got!r}"


@pytest.mark.parametrize("data, term, expected", [
    (b"  READY||", "|", "READY|"),
    (b"READY|  ", "|", "READY|"),
    (b"READY;END;END", ";END", "READY;END"),
    (b"READY;EN", ";END", "READY;EN"),
    (b"  2.5\r\n", "\r\n", "2.5"),
    (b"|", "|", ""),
])
def test_e2_removes_one_exact_suffix_then_whitespace(data: bytes, term: str, expected: str) -> None:
    got = decode_reply(data, term)
    assert got == expected, f"remove one {term!r} before stripping: got {got!r}"


@pytest.mark.parametrize("data", [b"\xff", b"READY\x80\n", b"\xc2\xb5\n"])
def test_e2_translates_decode_errors(data: bytes) -> None:
    with pytest.raises(ValueError) as caught:
        decode_reply(data)
    assert type(caught.value) is ValueError, "UnicodeDecodeError must become plain ValueError"


@pytest.mark.parametrize("term", ["", "\u00e9"])
def test_e2_validates_terminator(term: str) -> None:
    with pytest.raises(ValueError) as caught:
        decode_reply(b"READY", term)
    assert type(caught.value) is ValueError, "empty/non-ASCII terminators are invalid"


def test_e2_preserves_internal_terminators() -> None:
    got = decode_reply(b"  CH1|READY|", "|")
    assert got == "CH1|READY", f"only the trailing terminator is removed: {got!r}"


@pytest.mark.parametrize("header", ["*IDN?", "MEAS:VOLT?", ":SYST:ERR?"])
def test_e3_header_without_values(header: str) -> None:
    got = build(header)
    assert got == header, "a header alone needs no trailing space or terminator"


@pytest.mark.parametrize("value, expected", [
    (5, "VOLT 5"),
    (-2, "VOLT -2"),
    (0, "VOLT 0"),
    (2.5, "VOLT 2.5"),
    (1.0, "VOLT 1.0"),
    ("MIN", "VOLT MIN"),
])
def test_e3_scalar_arguments(value: str | int | float, expected: str) -> None:
    got = build("VOLT", value)
    assert got == expected, f"format the supplied value with str(): got {got!r}"


@pytest.mark.parametrize("enabled, expected", [(True, "OUTP ON"), (False, "OUTP OFF")])
def test_e3_boolean_arguments(enabled: bool, expected: str) -> None:
    got = build("OUTP", enabled)
    assert got == expected, f"SCPI boolean spelling is ON/OFF: got {got!r}"


@pytest.mark.parametrize("channels, expected", [
    (None, "MEAS:VOLT?"),
    ([], "MEAS:VOLT?"),
    ([1, 2], "MEAS:VOLT? (@1,2)"),
    ([3], "MEAS:VOLT? (@3)"),
    ([12, 2, 12], "MEAS:VOLT? (@12,2,12)"),
])
def test_e3_channel_arguments(channels: list[int] | None, expected: str) -> None:
    before = None if channels is None else channels.copy()
    got = build("MEAS:VOLT?", channels=channels)
    assert got == expected, f"format channels in supplied order: got {got!r}"
    assert channels == before, "building a command must not change the channel list"


def test_e3_multiple_values_and_literal_strings() -> None:
    got = build("SOUR:VOLT", 2.5, "MIN", True, channels=[3, 1])
    assert got == "SOUR:VOLT 2.5,MIN,ON,(@3,1)", f"use commas between all values: {got!r}"
    assert build("DISP:TEXT", '"Bench A"') == 'DISP:TEXT "Bench A"', "preserve supplied quotes"
    assert build("DISP:TEXT", "Bench A") == "DISP:TEXT Bench A", "do not add quotes"
    assert build("DISP:TEXT", "") == "DISP:TEXT ", "an empty string is still one value"
    assert build("VOLT", 5, channels=[]) == "VOLT 5", "empty channels add no comma"


@pytest.mark.parametrize("cmd", ["*IDN?", "MEAS:VOLT? (@1,2)", "  :SYST:ERR?\n", "\tREAD?\t(@3) ", "MEASure:VOLTage:DC?"])
def test_e4_detects_query_header(cmd: str) -> None:
    assert is_query(cmd) is True, f"header requests a reply: {cmd!r}"


@pytest.mark.parametrize("cmd", ["", " \t\r\n", "OUTP ON", 'DISP:TEXT "Ready?"', "DISP:TEXT Ready?", "SOUR?CE:VOLT 5"])
def test_e4_ignores_question_marks_outside_header_end(cmd: str) -> None:
    assert is_query(cmd) is False, f"header does not end in ?: {cmd!r}"


@pytest.mark.parametrize("header, expected", [
    ("MEASure:VOLTage:DC?", "MEAS:VOLT:DC?"),
    ("SOURce:CURRent", "SOUR:CURR"),
    ("SYSTem:ERRor?", "SYST:ERR?"),
])
def test_e4_shortens_manual_spelling(header: str, expected: str) -> None:
    got = short_form(header)
    assert got == expected, f"keep required uppercase letters from {header!r}: got {got!r}"


@pytest.mark.parametrize("header, expected", [
    (":SENSe1:VOLTage?", ":SENS1:VOLT?"),
    ("OUTPut12:STATe", "OUTP12:STAT"),
    ("*IDN?", "*IDN?"),
    ("MEAS:VOLT:DC?", "MEAS:VOLT:DC?"),
])
def test_e4_preserves_digits_and_punctuation(header: str, expected: str) -> None:
    got = short_form(header)
    assert got == expected, f"digits and SCPI punctuation must survive: got {got!r}"


def test_e4_shortening_keeps_query_meaning() -> None:
    header = short_form("MEASure:VOLTage:DC?")
    command = header + " (@1,2)"
    assert command == "MEAS:VOLT:DC? (@1,2)", f"unexpected meter request: {command!r}"
    assert is_query(command) is True, "shortened meter request still requires a reply"


class ScriptedTransport:
    """Check each call against a script; never connect to real hardware."""

    def __init__(self, script: list[tuple[str, str, str | BaseException | None]]) -> None:
        self.script = script
        self.calls: list[tuple[str, str]] = []

    def _step(self, method: str, command: str) -> str | None:
        index = len(self.calls)
        self.calls.append((method, command))
        assert index < len(self.script), f"unexpected extra call: {method}({command!r})"
        expected_method, expected_command, result = self.script[index]
        assert (method, command) == (expected_method, expected_command), (
            f"step {index + 1}: expected {expected_method}({expected_command!r}), "
            f"got {method}({command!r})"
        )
        if isinstance(result, BaseException):
            raise result
        return result

    def write(self, command: str) -> None:
        assert self._step("write", command) is None, "write() does not return a reply"

    def query(self, command: str) -> str:
        reply = self._step("query", command)
        assert isinstance(reply, str), "a scripted query needs a text reply"
        return reply


def power_up_script(
    volts: float = 5.0,
    amps: float = 0.2,
    identity: str = "FastTrack,PSU-30,SN0042,1.0",
    completion: str = "1",
    error: str = '0,"No error"',
) -> list[tuple[str, str, str | BaseException | None]]:
    return [
        ("query", "*IDN?", identity),
        ("write", "*RST", None),
        ("write", "*CLS", None),
        ("write", "OUTP OFF", None),
        ("write", "CURR " + str(amps), None),
        ("write", "VOLT " + str(volts), None),
        ("query", "*OPC?", completion),
        ("query", "SYST:ERR?", error),
        ("write", "OUTP ON", None),
    ]


@pytest.mark.parametrize("volts, amps, identity", [
    (5.0, 0.2, "FastTrack,PSU-30,SN0042,1.0"),
    (12.5, 1.25, "FastTrack,PSU-30,SN9000,2.3"),
    (0.0, 0.0, "FastTrack,PSU-30,SN0001,1.2"),
])
def test_e5_safe_sequence_and_query_replies(volts: float, amps: float, identity: str) -> None:
    transport = ScriptedTransport(power_up_script(volts, amps, identity))
    replies = safe_power_up(transport, volts, amps)
    assert replies == [identity, "1", '0,"No error"'], "return only query replies, in order"
    assert len(transport.calls) == len(transport.script), "finish every step, including OUTP ON"


@pytest.mark.parametrize("identity", [
    "OtherCo,PSU-30,SN0042,1.0",
    "FastTrack,DMM-10,SN0042,1.0",
    "FastTrack,PSU-300,SN0042,1.0",
    "FastTrack,PSU-30",
    "",
])
def test_e5_rejects_identity_before_writing(identity: str) -> None:
    transport = ScriptedTransport([("query", "*IDN?", identity)])
    with pytest.raises(RuntimeError) as caught:
        safe_power_up(transport, 5.0, 0.2)
    if isinstance(caught.value, NotImplementedError):
        raise caught.value
    assert str(caught.value) == f"unexpected identity: {identity.strip()}"
    assert transport.calls == [("query", "*IDN?")], "identity failure must send no settings"


@pytest.mark.parametrize("completion", ["0", "BUSY", ""])
def test_e5_requires_completed_operations(completion: str) -> None:
    transport = ScriptedTransport(power_up_script(completion=completion)[:7])
    with pytest.raises(RuntimeError) as caught:
        safe_power_up(transport, 5.0, 0.2)
    if isinstance(caught.value, NotImplementedError):
        raise caught.value
    assert str(caught.value) == f"operation did not complete: {completion.strip()}"
    assert len(transport.calls) == 7, "stop before the error query or enabling output"
    assert ("write", "OUTP ON") not in transport.calls


@pytest.mark.parametrize("error", [
    '-100,"Unknown command"',
    '-222,"Data out of range"',
    '-200,"Limit, rejected"',
    '  -350,"Queue overflow"  ',
])
def test_e5_first_error_keeps_output_off_and_preserves_diagnostic(error: str) -> None:
    script = power_up_script(error=error)[:8]
    script.extend([("query", "SYST:ERR?", '0,"No error"'), ("write", "OUTP ON", None)])
    transport = ScriptedTransport(script)
    with pytest.raises(RuntimeError) as caught:
        safe_power_up(transport, 5.0, 0.2)
    if isinstance(caught.value, NotImplementedError):
        raise caught.value
    assert str(caught.value) == error.strip(), "include the first error's code and full message"
    assert len(transport.calls) == 8, "raise immediately without reading another queue entry"
    assert ("write", "OUTP ON") not in transport.calls, "an instrument error must prevent power-on"


def test_e5_checks_stripped_replies_but_returns_original_text() -> None:
    identity = "  FastTrack,PSU-30,SN0042,1.0\n"
    completion = " 1\n"
    error = ' 0,"No error"\n'
    transport = ScriptedTransport(power_up_script(identity=identity, completion=completion, error=error))
    assert safe_power_up(transport, 5.0, 0.2) == [identity, completion, error]
    assert len(transport.calls) == 9, "empty error queue permits the final output-on command"


@pytest.mark.parametrize("index, failure, cleanup_failure", [
    (4, OSError("link lost"), None),
    (6, TimeoutError("no reply"), None),
    (6, KeyboardInterrupt("query interrupted"), None),
    (8, OSError("enable reply lost"), None),
    (8, OSError("enable reply lost"), TimeoutError("disable reply lost")),
    (8, KeyboardInterrupt("enable interrupted"), None),
    (8, KeyboardInterrupt("enable interrupted"), TimeoutError("disable reply lost")),
    (8, OSError("enable reply lost"), KeyboardInterrupt("disable interrupted")),
    (8, KeyboardInterrupt("enable interrupted"), KeyboardInterrupt("disable interrupted")),
])
def test_e5_transport_failure_stops_sequence_or_disables_output(
    index: int, failure: BaseException, cleanup_failure: BaseException | None,
) -> None:
    class StatefulTransport(ScriptedTransport):
        output_on = False

        def write(self, command: str) -> None:
            if command == "OUTP ON":
                self.output_on = True  # ON takes effect before its write raises.
            super().write(command)
            if command in ("*RST", "OUTP OFF"):
                self.output_on = False

    script = power_up_script()
    method, command, _ = script[index]
    script[index] = (method, command, failure)
    if index == 8:
        script.append(("write", "OUTP OFF", cleanup_failure))
    transport = StatefulTransport(script)
    with pytest.raises(type(failure), match=str(failure)) as caught:
        safe_power_up(transport, 5.0, 0.2)
    assert caught.value is failure, "propagate the original exception, even if OFF also fails"
    if index == 8:
        assert transport.calls == [(method, command) for method, command, _ in script], (
            "after ON fails, attempt OFF exactly once and send nothing else"
        )
        assert transport.output_on is (cleanup_failure is not None), (
            "OFF must disable the output that ON enabled, unless OFF itself fails"
        )
        if cleanup_failure is not None:
            assert getattr(caught.value, "__notes__", []) == [
                f"cleanup failed: OUTP OFF: {cleanup_failure!r}; output state unknown"
            ], "the original failure must report failed OFF and the unknown output state"
    else:
        assert len(transport.calls) == index + 1, "propagate connection failures without more calls"
        assert ("write", "OUTP ON") not in transport.calls
