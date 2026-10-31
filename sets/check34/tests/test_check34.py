from collections.abc import Callable, Iterator
from contextlib import contextmanager
import math
from pathlib import Path
import socket
import struct
import subprocess
import sys
from threading import Event, Thread
from typing import cast
import time
import zlib

import pytest

import starter.check34 as learner
from starter.check34 import (
    GapTracker, Limit, Measurement, Packet, Result, UdpListener,
    acquire_voltage, run_tool, check_all, exchange_lines, guarded_read, load_limits, parse_packet,
)


@pytest.mark.parametrize("code", [0, 7])
def test_e1_real_process_output_and_exit(code: int) -> None:
    script = "import sys; print('ready'); print('warning', file=sys.stderr); sys.exit(int(sys.argv[1]))"
    assert run_tool([sys.executable, "-c", script, str(code)], 5.0) == (code, "ready\n", "warning\n")


def test_e1_literal_arguments_and_no_input_mutation() -> None:
    args = [sys.executable, "-c", "import sys; print(sys.argv[1])", "rail 5; echo $(literal)"]
    before = args.copy()
    assert run_tool(args, 5.0) == (0, "rail 5; echo $(literal)\n", "")
    assert args == before


def test_e1_utf8_and_empty_output() -> None:
    assert run_tool([sys.executable, "-c", r"import sys; sys.stdout.buffer.write(b'rail \xc2\xb5V')"], 5.0) == (0, "rail \u00b5V", "")
    assert run_tool([sys.executable, "-c", "pass"], 5.0) == (0, "", "")


def test_e1_timeout_reaps_process(monkeypatch: pytest.MonkeyPatch) -> None:
    real_popen = subprocess.Popen
    children: list[subprocess.Popen[str]] = []

    def tracked_popen(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", tracked_popen)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            run_tool([sys.executable, "-c", "import threading; threading.Event().wait(30)"], 0.2)
        assert children and all(child.poll() is not None for child in children), "timeout must kill and wait for the child"
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=2.0)


def test_e1_launch_error_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_tool([str(tmp_path / "missing-station-tool")], 5.0)


def _correct_trip(value: float, low: float) -> bool:
    return value < low


def test_e2_accepts_correct_rule() -> None:
    assert learner.test_e2_trip_boundary(_correct_trip) is None, "a pytest test returns None"


def test_e2_catches_inclusive_mutant() -> None:
    learner.test_e2_trip_boundary(_correct_trip)
    with pytest.raises(AssertionError):
        learner.test_e2_trip_boundary(lambda value, low: value <= low)


def test_e2_catches_never_trip_mutant() -> None:
    learner.test_e2_trip_boundary(_correct_trip)
    with pytest.raises(AssertionError):
        learner.test_e2_trip_boundary(lambda value, low: False)


def test_e2_catches_always_trip_mutant() -> None:
    learner.test_e2_trip_boundary(_correct_trip)
    with pytest.raises(AssertionError):
        learner.test_e2_trip_boundary(lambda value, low: True)


def test_e2_catches_high_side_mutant() -> None:
    learner.test_e2_trip_boundary(_correct_trip)
    with pytest.raises(AssertionError):
        learner.test_e2_trip_boundary(lambda value, low: value != low)


def _limits_file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "station limits.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_e3_valid_csv(tmp_path: Path) -> None:
    path = _limits_file(tmp_path, '# station limits\n\n name , low , high , unit \n"rail, main", 4.5,5.5,V\n fan,,9,A\naux,-2,,V\n# end\n')
    assert load_limits(path) == {
        "rail, main": Limit(4.5, 5.5, "V"), "fan": Limit(None, 9.0, "A"),
        "aux": Limit(-2.0, None, "V"),
    }


def test_e3_header_only_and_equal_bounds(tmp_path: Path) -> None:
    assert load_limits(_limits_file(tmp_path, "name,low,high,unit\n")) == {}
    assert load_limits(_limits_file(tmp_path, "name,low,high,unit\nx,0,0,V\n"))["x"] == Limit(0, 0, "V")


@pytest.mark.parametrize("row", [
    "rail,1,2", "rail,1,2,V,extra", ",1,2,V", "rail,1,2,", "rail,,,V",
    "rail,3,2,V", "rail,no,2,V", "rail,1,nan,V", "rail,-inf,2,V",
    '"unterminated,1,2,V',
])
def test_e3_bad_rows_name_physical_line(tmp_path: Path, row: str) -> None:
    path = _limits_file(tmp_path, "# notes\nname,low,high,unit\n\n# blank above\n" + row + "\n")
    with pytest.raises(ValueError, match=r"\bline 5\b"):
        load_limits(path)


def test_e3_duplicate_trimmed_name(tmp_path: Path) -> None:
    path = _limits_file(tmp_path, "name,low,high,unit\nrail,1,2,V\n rail ,1,2,V\n")
    with pytest.raises(ValueError, match=r"\bline 3\b"):
        load_limits(path)


@pytest.mark.parametrize("text,number", [("wrong,header\n", 1), ("# skip\nwrong,header\n", 2), ("# only comments\n\n", 1), ("", 1)])
def test_e3_bad_or_missing_header(tmp_path: Path, text: str, number: int) -> None:
    with pytest.raises(ValueError, match=rf"\bline {number}\b"):
        load_limits(_limits_file(tmp_path, text))


def test_e3_missing_file_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_limits(tmp_path / "missing.csv")


class FakeTransport:
    def __init__(self, reply: str | Exception = "5.125\n", fail_write: str | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self.reply = reply
        self.fail_write = fail_write

    def write(self, command: str) -> None:
        self.calls.append(("write", command))
        if command == self.fail_write:
            raise OSError("write failed")

    def query(self, command: str) -> str:
        self.calls.append(("query", command))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


def test_e4_exact_sequence(transport: FakeTransport) -> None:
    assert acquire_voltage(transport, 2, 5.25) == 5.125
    assert transport.calls == [
        ("write", "INST:NSEL 2"), ("write", "VOLT 5.250"),
        ("write", "OUTP ON"), ("query", "MEAS:VOLT?"),
    ], "select, configure, enable, then measure; no extra calls"


@pytest.mark.parametrize("channel,volts", [(0, 5.0), (4, 5.0), (1, -0.001), (1, 30.001), (1, math.nan), (1, math.inf)])
def test_e4_validates_before_writing(transport: FakeTransport, channel: int, volts: float) -> None:
    with pytest.raises(ValueError):
        acquire_voltage(transport, channel, volts)
    assert transport.calls == [], "invalid requests must have no transport side effects"


@pytest.mark.parametrize("channel,volts", [(1, 0.0), (3, 30.0)])
def test_e4_boundary_setpoints(transport: FakeTransport, channel: int, volts: float) -> None:
    acquire_voltage(transport, channel, volts)
    assert transport.calls[:2] == [("write", f"INST:NSEL {channel}"), ("write", f"VOLT {volts:.3f}")]


@pytest.mark.parametrize("reply", ["", "overload", "nan", "-inf"])
def test_e4_rejects_bad_reply(reply: str) -> None:
    with pytest.raises(ValueError):
        acquire_voltage(FakeTransport(reply), 1, 2.0)


def test_e4_propagates_transport_failures() -> None:
    error = TimeoutError("no reply")
    transport = FakeTransport(error)
    with pytest.raises(TimeoutError) as caught:
        acquire_voltage(transport, 1, 2.0)
    assert caught.value is error
    broken = FakeTransport(fail_write="VOLT 2.000")
    with pytest.raises(OSError):
        acquire_voltage(broken, 1, 2.0)
    assert broken.calls == [("write", "INST:NSEL 1"), ("write", "VOLT 2.000")]


def test_e5_order_missing_and_extra() -> None:
    limits = {"z": Limit(0, 5, "V"), "b": Limit(None, 3, "A")}
    readings = [Measurement("a", 9, "V"), Measurement("z", 5, "V"), Measurement("x", 1, "A")]
    assert check_all(iter(readings), limits) == [
        Result("b", None, "ERROR", "not measured"), Result("z", 5, "PASS", "within limits"),
        Result("a", 9, "ERROR", "no limit"), Result("x", 1, "ERROR", "no limit"),
    ], "limit names come first, then sorted unexpected names"


@pytest.mark.parametrize("value,low,high,status,message", [
    (0, 0, 2, "PASS", "within limits"), (2, 0, 2, "PASS", "within limits"),
    (-1, 0, None, "FAIL", "below low"), (3, None, 2, "FAIL", "above high"),
    (500, 0, None, "PASS", "within limits"), (-500, None, 2, "PASS", "within limits"),
])
def test_e5_bounds(value: float, low: float | None, high: float | None, status: str, message: str) -> None:
    assert check_all([Measurement("rail", value, "V")], {"rail": Limit(low, high, "V")}) == [Result("rail", value, status, message)]


def test_e5_duplicate_precedence() -> None:
    readings = [Measurement("rail", math.nan, "mV"), Measurement("extra", 1, "V"), Measurement("rail", 2, "V"), Measurement("extra", 2, "V")]
    assert check_all(readings, {"rail": Limit(0, 3, "V")}) == [
        Result("rail", None, "ERROR", "duplicate measurement"),
        Result("extra", None, "ERROR", "duplicate measurement"),
    ]


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_e5_nonfinite_is_error(value: float) -> None:
    result = check_all([Measurement("rail", value, "V")], {"rail": Limit(0, 3, "V")})[0]
    assert (result.name, result.status, result.message) == ("rail", "ERROR", "non-finite reading")
    assert result.value is value or result.value == value


def test_e5_unit_precedes_numeric_checks() -> None:
    result = check_all([Measurement("rail", math.nan, "mV")], {"rail": Limit(0, 3, "V")})[0]
    assert (result.status, result.message) == ("ERROR", "unit mismatch")
    assert check_all([Measurement("rail", -1, "v")], {"rail": Limit(0, 3, "V")})[0].message == "unit mismatch"


def test_e5_empty_and_no_input_mutation() -> None:
    assert check_all([], {}) == []
    measurements = [Measurement("rail", 2, "V")]
    limits = {"rail": Limit(0, 3, "V")}
    assert check_all(measurements, limits) == check_all(iter(measurements), limits)
    assert measurements == [Measurement("rail", 2, "V")]
    assert limits == {"rail": Limit(0, 3, "V")}


@contextmanager
def _tcp_peer(chunks: list[bytes], hold: bool = False) -> Iterator[tuple[socket.socket, list[bytes]]]:
    """Real loopback server; stop coordination needs no scheduling sleeps."""
    release = Event()
    requests: list[bytes] = []
    errors: list[BaseException] = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(2.0)

        def serve() -> None:
            try:
                connection, _address = server.accept()
                with connection:
                    connection.settimeout(2.0)
                    request = b""
                    while b"\n" not in request:
                        data = connection.recv(4096)
                        if not data:
                            return  # A starter stub can exit before sending.
                        request += data
                    requests.append(request)
                    for chunk in chunks:
                        connection.sendall(chunk)
                    if hold:
                        release.wait(timeout=2.0)
            except BaseException as error:
                errors.append(error)

        worker = Thread(target=serve, name="check34-tcp-fake")
        worker.start()
        try:
            with socket.create_connection(server.getsockname(), timeout=2.0) as client:
                yield client, requests
        finally:
            release.set()
            worker.join(timeout=3.0)
            assert not worker.is_alive(), "fake server thread must be joined"
            assert not errors, f"fake server failed: {errors}"


class ScriptedConnection:
    """Force receive boundaries, which TCP itself is free to regroup."""
    def __init__(self, chunks: list[bytes], error: OSError | None = None) -> None:
        self.chunks = chunks.copy()
        self.error = error
        self.sent: list[bytes] = []

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def recv(self, size: int) -> bytes:
        if self.error is not None:
            raise self.error
        assert self.chunks, "stop receiving once the requested replies are complete"
        chunk = self.chunks.pop(0)
        assert len(chunk) <= size
        return chunk


def test_e6_real_tcp_request_and_replies() -> None:
    with _tcp_peer([b"5.", b"125\nOK\n"]) as (connection, requests):
        assert exchange_lines(connection, "MEAS:VOLT?", 2) == ["5.125", "OK"]
        assert requests == [b"MEAS:VOLT?\n"], "send the command with exactly one newline"
        assert connection.fileno() != -1, "the caller owns this socket"
        assert connection.gettimeout() == 2.0, "preserve the supplied timeout"


@pytest.mark.parametrize("chunks,expected", [
    ([b"5.", b"125", b"\nO", b"K\n"], ["5.125", "OK"]),
    ([b"5.125\nOK\n"], ["5.125", "OK"]),
    ([b"\n 5.0 \n"], ["", " 5.0 "]),
    ([b"READY\n"], ["READY"]),
])
def test_e6_deterministic_split_and_coalesced_reads(chunks: list[bytes], expected: list[str]) -> None:
    peer = ScriptedConnection(chunks)
    assert exchange_lines(cast(socket.socket, peer), "READ?", len(expected)) == expected
    assert peer.sent == [b"READ?\n"]


@pytest.mark.parametrize("chunks", [[], [b"partial"], [b"first\nunfinished"]])
def test_e6_early_eof_is_error(chunks: list[bytes]) -> None:
    with _tcp_peer(chunks) as (connection, _requests):
        with pytest.raises(ConnectionError):
            exchange_lines(connection, "READ?", 2)


@pytest.mark.parametrize("chunks", [[], [b"partial"], [b"first\n"]])
def test_e6_silent_or_stalled_reply_times_out(chunks: list[bytes]) -> None:
    with _tcp_peer(chunks, hold=True) as (connection, _requests):
        connection.settimeout(0.1)
        with pytest.raises(TimeoutError):
            exchange_lines(connection, "READ?", 2)
        assert connection.fileno() != -1, "leave cleanup to the caller even after timeout"


def test_e6_other_socket_error_propagates() -> None:
    error = OSError("instrument disconnected")
    peer = ScriptedConnection([], error)
    with pytest.raises(OSError) as caught:
        exchange_lines(cast(socket.socket, peer), "READ?", 1)
    assert caught.value is error


def _operation(calls: list[str], name: str, error: BaseException | None = None) -> Callable[[], None]:
    def run() -> None:
        calls.append(name)
        if error is not None:
            raise error
    return run


def _measurement(calls: list[str], error: BaseException | None = None) -> Callable[[], float]:
    def run() -> float:
        calls.append("measure")
        if error is not None:
            raise error
        return 4.75
    return run


def test_e7_success_and_return_value() -> None:
    calls: list[str] = []
    value = guarded_read(_operation(calls, "enable"), _measurement(calls), _operation(calls, "disable"))
    assert value == 4.75
    assert calls == ["enable", "measure", "disable"]


@pytest.mark.parametrize("phase", ["enable", "measure"])
def test_e7_original_failure_still_disables(phase: str) -> None:
    calls: list[str] = []
    error = ValueError("station failure")
    with pytest.raises(ValueError) as caught:
        guarded_read(_operation(calls, "enable", error if phase == "enable" else None), _measurement(calls, error if phase == "measure" else None), _operation(calls, "disable"))
    assert caught.value is error
    assert calls == (["enable", "disable"] if phase == "enable" else ["enable", "measure", "disable"])


def test_e7_cleanup_error_after_success_propagates() -> None:
    calls: list[str] = []
    error = OSError("output off failed")
    with pytest.raises(OSError) as caught:
        guarded_read(_operation(calls, "enable"), _measurement(calls), _operation(calls, "disable", error))
    assert caught.value is error
    assert calls == ["enable", "measure", "disable"]


@pytest.mark.parametrize("phase", ["enable", "measure"])
def test_e7_cleanup_does_not_replace_original(phase: str) -> None:
    calls: list[str] = []
    original = TimeoutError("lost device")
    with pytest.raises(TimeoutError) as caught:
        guarded_read(_operation(calls, "enable", original if phase == "enable" else None), _measurement(calls, original if phase == "measure" else None), _operation(calls, "disable", OSError("cleanup failed")))
    assert caught.value is original
    assert calls.count("disable") == 1


def test_e7_operator_interrupt_still_disables() -> None:
    calls: list[str] = []
    error = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt) as caught:
        guarded_read(_operation(calls, "enable"), _measurement(calls, error), _operation(calls, "disable", RuntimeError("cleanup failed")))
    assert caught.value is error
    assert calls == ["enable", "measure", "disable"]


def _packet(seq: int = 42, timestamp: int = 123456789, readings: list[tuple[int, float]] | None = None, sync: int = 0xEB90) -> bytes:
    if readings is None:
        readings = [(7, 1.5), (2, -2.25)]
    body = struct.pack(">HHQB", sync, seq, timestamp, len(readings))
    body += b"".join(struct.pack(">Bf", channel, value) for channel, value in readings)
    return body + struct.pack(">I", zlib.crc32(body))


def test_e8_valid_and_empty_packets() -> None:
    assert parse_packet(_packet()) == Packet(42, 123456789, {7: 1.5, 2: -2.25})
    assert parse_packet(_packet(65535, 2**64 - 1, [])) == Packet(65535, 2**64 - 1, {})
    assert parse_packet(_packet(0, 0, [(255, 0.1)])).readings[255] == pytest.approx(0.1)
    assert parse_packet(_packet(readings=[(0, math.inf)])).readings[0] == math.inf


@pytest.mark.parametrize("length", [0, 1, 12, 13, 16])
def test_e8_short_packet(length: int) -> None:
    with pytest.raises(ValueError):
        parse_packet(bytes(length))


def test_e8_sync_and_length_validation() -> None:
    packets = [_packet(sync=0), _packet()[:-1], _packet() + b"\x00", _packet() + _packet()]
    count_bad = bytearray(_packet())
    count_bad[12] = 3
    count_bad[-4:] = struct.pack(">I", zlib.crc32(count_bad[:-4]))
    packets.append(bytes(count_bad))
    for data in packets:
        with pytest.raises(ValueError):
            parse_packet(data)


@pytest.mark.parametrize("offset", [2, 5, 14, -1])
def test_e8_crc_covers_header_and_values(offset: int) -> None:
    damaged = bytearray(_packet())
    damaged[offset] ^= 1
    with pytest.raises(ValueError):
        parse_packet(bytes(damaged))


def test_e8_duplicate_channels_with_valid_crc() -> None:
    with pytest.raises(ValueError):
        parse_packet(_packet(readings=[(3, 1.0), (3, 2.0)]))


def test_e8_full_channel_count() -> None:
    readings = [(channel, float(channel)) for channel in range(255)]
    assert parse_packet(_packet(readings=readings)).readings == dict(readings)


def test_e9_forward_gaps_and_late_recovery() -> None:
    tracker = GapTracker()
    assert (tracker.received, tracker.duplicates, tracker.out_of_order, tracker.missing) == (0, 0, 0, set())
    assert tracker.update(10) == []
    assert tracker.update(13) == [11, 12]
    assert tracker.update(11) == []
    assert tracker.missing == {12}
    assert tracker.update(14) == [], "late arrivals must not move the forward anchor"
    assert (tracker.received, tracker.duplicates, tracker.out_of_order) == (4, 0, 1)


def test_e9_duplicates_take_precedence() -> None:
    tracker = GapTracker()
    for seq in [10, 13, 11, 11, 13]:
        tracker.update(seq)
    assert tracker.missing == {12}
    assert (tracker.received, tracker.duplicates, tracker.out_of_order) == (5, 2, 1)


def test_e9_wraparound_and_late_wrap_recovery() -> None:
    tracker = GapTracker()
    assert tracker.update(65534) == []
    assert tracker.update(1) == [65535, 0]
    assert tracker.update(0) == []
    assert tracker.update(2) == []
    assert tracker.missing == {65535}
    adjacent = GapTracker()
    adjacent.update(65535)
    assert adjacent.update(0) == []
    assert not adjacent.missing


def test_e9_recent_window_includes_duplicate_calls() -> None:
    boundary = GapTracker()
    for seq in range(1024):
        boundary.update(seq)
    assert boundary.update(0) == []
    assert (boundary.duplicates, boundary.out_of_order) == (1, 0), "check membership before eviction"
    tracker = GapTracker()
    tracker.update(0)
    tracker.update(1)
    for _ in range(1023):
        tracker.update(1)
    assert tracker.update(0) == [], "0 has left the last 1024 arrivals and is now late"
    assert (tracker.received, tracker.duplicates, tracker.out_of_order) == (1026, 1023, 1)
    assert tracker.update(0) == []
    assert tracker.duplicates == 1024


@pytest.mark.parametrize("bad", [-1, 65536])
def test_e9_invalid_sequence_does_not_mutate(bad: int) -> None:
    tracker = GapTracker()
    tracker.update(2)
    with pytest.raises(ValueError):
        tracker.update(bad)
    assert (tracker.received, tracker.duplicates, tracker.out_of_order, tracker.missing) == (1, 0, 0, set())
    assert tracker.update(4) == [3]


def test_e9_half_range_is_late_and_gap_lists_are_independent() -> None:
    tracker = GapTracker()
    tracker.update(100)
    assert tracker.update(32868) == []
    assert tracker.out_of_order == 1
    gaps = tracker.update(103)
    assert gaps == [101, 102]
    gaps.clear()
    assert tracker.missing == {101, 102}, "returned gap lists must not alias retained state"



@contextmanager
def _udp_listener() -> Iterator[UdpListener]:
    listener = UdpListener()
    try:
        yield listener
    finally:
        try:
            listener.stop()
        finally:
            # Harness fallback also cleans up an unfinished learner stop method.
            listener._stopping.set()
            listener._thread.join(timeout=2.0)
            assert not listener._thread.is_alive(), "listener thread must be joined"
            listener._socket.close()


def test_e10_receives_whole_datagrams_including_empty() -> None:
    with _udp_listener() as listener:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.settimeout(2.0)
            for packet in [b"rail=5.0", b"", b"\x00\xff\n", b"x" * 4096]:
                sender.sendto(packet, listener.address)
                assert listener.packets.get(timeout=2.0) == packet, "one queue item per datagram, including empty bytes"


def test_e10_timeout_keeps_listener_running() -> None:
    with _udp_listener() as listener:
        assert listener.idle.wait(timeout=2.0), "receive timeout should return None"
        assert listener._thread.is_alive(), "a quiet instrument is not a stopped listener"
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.settimeout(2.0)
            sender.sendto(b"after idle", listener.address)
        assert listener.packets.get(timeout=2.0) == b"after idle"


def test_e10_idle_stop_joins_closes_and_is_repeatable() -> None:
    with _udp_listener() as listener:
        started = time.perf_counter()
        listener.stop()
        assert time.perf_counter() - started < 1.5, "stop must have a bounded join"
        assert not listener._thread.is_alive()
        assert listener._socket.fileno() == -1, "worker cleanup closes the socket"
        assert listener.stop() is None

    class StuckThread:
        def __init__(self) -> None:
            self.join_timeout: float | None = None

        def join(self, timeout: float | None = None) -> None:
            self.join_timeout = timeout

        def is_alive(self) -> bool:
            return True

    # Script a stuck worker without leaving a real thread running.
    stuck = UdpListener.__new__(UdpListener)
    worker = StuckThread()
    stuck._thread = cast(Thread, worker)
    stuck._stopping = Event()
    stuck.error = None
    with pytest.raises(TimeoutError):
        stuck.stop()
    assert stuck._stopping.is_set(), "request stop before waiting"
    assert worker.join_timeout == 1.0, "join must have a one-second timeout"


def test_e10_instances_stop_independently() -> None:
    with _udp_listener() as first, _udp_listener() as second:
        first.stop()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.settimeout(2.0)
            sender.sendto(b"second station", second.address)
        assert second.packets.get(timeout=2.0) == b"second station"
        assert second._thread.is_alive()


def test_e10_receive_does_not_hide_other_errors() -> None:
    error = OSError("receiver failed")

    class BrokenSocket:
        def recvfrom(self, size: int) -> tuple[bytes, tuple[str, int]]:
            raise error

    listener = UdpListener.__new__(UdpListener)
    listener._socket = cast(socket.socket, BrokenSocket())
    with pytest.raises(OSError) as caught:
        listener.receive_once()
    assert caught.value is error


def test_e10_stop_surfaces_background_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    error = OSError("background receive failed")
    receive_attempted = Event()

    def fail_receive(self: UdpListener) -> bytes | None:
        receive_attempted.set()
        raise error

    monkeypatch.setattr(UdpListener, "receive_once", fail_receive)
    with _udp_listener() as listener:
        try:
            assert receive_attempted.wait(timeout=2.0), "worker must attempt receive before stop"
            with pytest.raises(OSError) as caught:
                listener.stop()
            assert caught.value is error
            assert not listener._thread.is_alive()
            assert listener._socket.fileno() == -1
        finally:
            listener.error = None  # Allow the harness's repeated stop to finish.
