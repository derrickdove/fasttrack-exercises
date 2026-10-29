from collections import deque
from collections.abc import Callable
import math
from pathlib import Path
import struct
import time
import zlib

import pytest

import starter.check30 as learner
from starter.check30 import (
    GapTracker, Limit, Measurement, Packet, Result, WindowAlarm,
    acquire_voltage, blocked_tools, check_all, guarded_read, load_limits, parse_packet,
)


def test_e1_sorted_unique_blockers() -> None:
    exits = [("scope", 0), ("psu", 1), ("dmm", -15), ("psu", 0), ("dmm", 2)]
    assert blocked_tools(exits) == ["dmm", "psu"], "any failed attempt blocks that tool"
    assert exits[0] == ("scope", 0), "do not mutate the input"


def test_e1_empty_and_success() -> None:
    assert blocked_tools([]) == []
    assert blocked_tools([("psu", 0), ("psu", 0)]) == []


@pytest.mark.parametrize("code", [-9, 1, 2, 143])
def test_e1_all_nonzero_codes_block(code: int) -> None:
    assert blocked_tools([("telemetry", code)]) == ["telemetry"]


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


def test_e6_warmup_and_eviction() -> None:
    alarm = WindowAlarm(3, 2.0)
    assert [alarm.add(value) for value in [1, 2, 3, 4, 0]] == [None, None, False, True, True]
    assert isinstance(alarm.values, deque), "use a deque for the station window"
    assert list(alarm.values) == [3, 4, 0]
    assert alarm.values.maxlen == 3
    assert (alarm.size, alarm.threshold) == (3, 2.0)


def test_e6_size_one_and_instances() -> None:
    first, second = WindowAlarm(1, 0), WindowAlarm(2, 0)
    assert first.add(0) is False
    assert first.add(1) is True
    assert second.add(1) is None
    assert list(first.values) == [1]


@pytest.mark.parametrize("size,threshold", [(0, 1), (-1, 1), (1, math.nan), (1, math.inf)])
def test_e6_invalid_configuration(size: int, threshold: float) -> None:
    with pytest.raises(ValueError):
        WindowAlarm(size, threshold)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_e6_bad_reading_leaves_window_unchanged(bad: float) -> None:
    alarm = WindowAlarm(2, 1)
    assert alarm.add(1) is None
    with pytest.raises(ValueError):
        alarm.add(bad)
    assert list(alarm.values) == [1]
    assert alarm.add(1) is False


def test_e6_fast_enough() -> None:
    alarm = WindowAlarm(20_000, 1.0)
    started = time.perf_counter()
    last = None
    for _ in range(200_000):
        last = alarm.add(1.0)
    elapsed = time.perf_counter() - started
    assert last is False
    assert len(alarm.values) == 20_000
    assert elapsed <= 2.0, f"200,000 updates took {elapsed:.3f}s; keep a running sum"


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

