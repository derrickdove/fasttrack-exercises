"""Behavior checks for the station review; packet fixtures are independent."""
import binascii
from pathlib import Path
import struct

import pytest

from starter.review4 import (
    FrameBuffer, build_packet, capture_report, gap_report, limit_failures,
    parse_packet, sample_mux,
)


def wire(seq: int, readings: list[tuple[int, int]]) -> bytes:
    body = struct.pack("<2sHB", b"\xc3\x5a", seq, len(readings))
    body += b"".join(struct.pack("<Bh", ch, mv) for ch, mv in readings)
    return body + struct.pack("<H", binascii.crc_hqx(body, 0xffff))


def checksum(body: bytes) -> bytes:
    return body + struct.pack("<H", binascii.crc_hqx(body, 0xffff))


def frame(payload: bytes) -> bytes:
    return len(payload).to_bytes(2, "little") + payload


def write_capture(path: Path, payloads: list[tuple[int, bytes]]) -> None:
    data = struct.pack("<IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)
    for index, (port, payload) in enumerate(payloads):
        ethernet = b"\x00" * 12 + b"\x08\x00"
        # Four bytes of IPv4 options ensure the loader honors the header length.
        ip = struct.pack("!BBHHHBBH4s4s", 0x46, 0, 32 + len(payload),
                         index, 0, 64, 17, 0, b"\x7f\x00\x00\x01", b"\x7f\x00\x00\x01")
        udp = struct.pack("!HHHH", 9000, port, 8 + len(payload), 0)
        packet = ethernet + ip + b"\x01\x01\x01\x00" + udp + payload
        data += struct.pack("<IIII", 1000, index, len(packet), len(packet)) + packet
    path.write_bytes(data)


@pytest.fixture
def capture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "review.pcap"


@pytest.mark.parametrize("seq,readings", [
    (0, {}), (0x1234, {7: -250, 2: 1200}),
    (65535, {32: 32767, 1: -32768}),
])
def test_e1_little_endian_and_crc(seq: int, readings: dict[int, int]) -> None:
    got = build_packet(seq, readings)
    expected = wire(seq, sorted(readings.items()))
    assert got == expected, f"sequence {seq}: expected wire bytes {expected.hex()}, got {got.hex()}"


def test_e1_eight_readings_and_no_mutation() -> None:
    readings = {ch: ch * -10 for ch in range(8, 0, -1)}
    original = list(readings.items())
    assert build_packet(42, readings) == wire(42, sorted(readings.items()))
    assert list(readings.items()) == original, "packing must not mutate the readings dictionary"


@pytest.mark.parametrize("seq,readings", [(-1, {}), (65536, {}), (0, dict.fromkeys(range(1, 10), 0))])
def test_e1_rejects_sequence_and_count(seq: int, readings: dict[int, int]) -> None:
    with pytest.raises(ValueError):
        build_packet(seq, readings)


@pytest.mark.parametrize("readings", [{0: 0}, {33: 0}, {1: -32769}, {1: 32768}])
def test_e1_rejects_reading_ranges(readings: dict[int, int]) -> None:
    with pytest.raises(ValueError):
        build_packet(12, readings)


@pytest.mark.parametrize("seq,readings", [
    (0, []), (65535, [(32, -32768), (1, 32767)]),
    (0x1234, [(7, -250), (2, 1200)]),
    (42, [(ch, ch) for ch in range(1, 9)]),
])
def test_e2_decodes_whole_packet(seq: int, readings: list[tuple[int, int]]) -> None:
    assert parse_packet(wire(seq, readings)) == (seq, dict(readings)), "decode all readings, including signed values"


@pytest.mark.parametrize("packet", [b"", b"\xc3", b"\xc3\x5a\x00\x00\x00\x00", wire(3, [])[:-1], wire(3, []) + b"\x00"])
def test_e2_rejects_short_or_extra_bytes(packet: bytes) -> None:
    with pytest.raises(ValueError):
        parse_packet(packet)


@pytest.mark.parametrize("body", [
    b"NO" + wire(1, [])[:-2][2:],
    struct.pack("<2sHB", b"\xc3\x5a", 1, 1),
    wire(1, [(ch, 0) for ch in range(1, 10)])[:-2],
])
def test_e2_rejects_sync_count_and_length(body: bytes) -> None:
    with pytest.raises(ValueError):
        parse_packet(checksum(body))


def test_e2_checks_crc() -> None:
    packet = bytearray(wire(7, [(2, 1200)]))
    packet[6] ^= 1
    with pytest.raises(ValueError):
        parse_packet(bytes(packet))


@pytest.mark.parametrize("readings", [[(0, 1)], [(33, 1)], [(2, 1), (2, 2)]])
def test_e2_rejects_channel_errors_with_valid_crc(readings: list[tuple[int, int]]) -> None:
    with pytest.raises(ValueError):
        parse_packet(wire(5, readings))


def test_e3_retains_split_header_and_body() -> None:
    reader = FrameBuffer()
    assert reader.feed(b"\x03") == [], "one length byte cannot complete a frame"
    assert reader.feed(b"\x00A") == [], "retain the partial payload"
    assert reader.feed(b"B") == []
    assert reader.feed(b"C") == [b"ABC"]
    assert reader.feed(b"") == []


def test_e3_coalesced_empty_and_binary_payloads() -> None:
    reader = FrameBuffer()
    assert reader.feed(frame(b"") + frame(b"\x00\xff") + frame(b"last")) == [b"", b"\x00\xff", b"last"]
    assert reader.feed(frame(b"next") + b"\x02") == [b"next"]
    assert reader.feed(b"\x00ok") == [b"ok"], "keep the next header byte after returning a frame"


def test_e3_every_byte_can_arrive_separately() -> None:
    reader = FrameBuffer()
    stream = frame(b"RESET") + frame(b"") + frame(b"\xc3\x5a")
    got: list[bytes] = []
    for value in stream:
        got.extend(reader.feed(bytes([value])))
    assert got == [b"RESET", b"", b"\xc3\x5a"]


def test_e3_exact_limit_and_independent_instances() -> None:
    first, second = FrameBuffer(), FrameBuffer()
    assert first.feed(frame(b"A" * 4096)[:-1]) == []
    assert second.feed(frame(b"B")) == [b"B"]
    assert first.feed(b"A") == [b"A" * 4096], "4096 is allowed and little-endian"


@pytest.mark.parametrize("size", [4097, 65535])
def test_e3_oversize_raises_on_prefix_and_resets(size: int) -> None:
    reader = FrameBuffer()
    prefix = size.to_bytes(2, "little")
    assert reader.feed(prefix[:1]) == []
    with pytest.raises(ValueError):
        reader.feed(prefix[1:] + frame(b"discard"))
    assert reader.feed(frame(b"fresh")) == [b"fresh"], "discard all pending bytes on an oversized prefix"
    with pytest.raises(ValueError):
        reader.feed(frame(b"also discarded") + prefix)
    assert reader.feed(b"") == []


@pytest.mark.parametrize("seqs,expected", [
    ([], dict(received=0, missing=0, duplicates=0, out_of_order=0, longest_gap=0)),
    ([42], dict(received=1, missing=0, duplicates=0, out_of_order=0, longest_gap=0)),
    ([10, 11, 15, 17], dict(received=4, missing=4, duplicates=0, out_of_order=0, longest_gap=3)),
])
def test_e4_empty_single_and_forward(seqs: list[int], expected: dict[str, int]) -> None:
    assert gap_report(seqs) == expected, f"gap counts for {seqs} must be {expected}"


def test_e4_wraparound_does_not_create_a_huge_gap() -> None:
    assert gap_report([65534, 1, 1, 0, 3, 4]) == dict(
        received=6, missing=3, duplicates=1, out_of_order=1, longest_gap=2)


@pytest.mark.parametrize("seqs,expected", [
    ([10, 12, 11, 11, 12, 13], dict(received=6, missing=1, duplicates=2, out_of_order=1, longest_gap=1)),
    ([100, 102, 99, 103], dict(received=4, missing=1, duplicates=0, out_of_order=1, longest_gap=1)),
    ([1, 32769], dict(received=2, missing=0, duplicates=0, out_of_order=1, longest_gap=0)),
])
def test_e4_late_packets_never_repair_or_move_newest(seqs: list[int], expected: dict[str, int]) -> None:
    assert gap_report(seqs) == expected, "late sequences stay in seen history but never move newest"


@pytest.mark.parametrize("seqs", [[-1], [65536], [10, -1]])
def test_e4_rejects_invalid_sequence(seqs: list[int]) -> None:
    with pytest.raises(ValueError):
        gap_report(seqs)


def test_e4_keeps_arrival_order_and_input() -> None:
    seqs = [7, 9, 8, 10]
    assert gap_report(seqs)["out_of_order"] == 1, "sorting would erase late arrivals"
    assert seqs == [7, 9, 8, 10], "do not modify the input"


def test_e5_supplied_capture(capture_path: Path) -> None:
    assert capture_report(capture_path, 5005) == dict(
        received=6, missing=3, duplicates=1, out_of_order=1, longest_gap=2, bad_packets=2)


def test_e5_filters_destination_port(capture_path: Path) -> None:
    assert capture_report(capture_path, 6006) == dict(
        received=1, missing=0, duplicates=0, out_of_order=0, longest_gap=0, bad_packets=0)
    assert capture_report(capture_path, 1234) == dict(
        received=0, missing=0, duplicates=0, out_of_order=0, longest_gap=0, bad_packets=0)


def test_e5_bad_payloads_do_not_advance_sequence(tmp_path: Path) -> None:
    path = tmp_path / "other.pcap"
    write_capture(path, [(5005, wire(10, [])), (5005, wire(11, [(2, 1), (2, 2)])),
                         (5005, b""), (6006, b"garbage"), (5005, wire(12, []))])
    assert capture_report(path, 5005) == dict(
        received=2, missing=1, duplicates=0, out_of_order=0, longest_gap=1, bad_packets=2)


def test_e5_empty_capture(tmp_path: Path) -> None:
    path = tmp_path / "empty.pcap"
    write_capture(path, [])
    assert capture_report(path, 0) == dict(
        received=0, missing=0, duplicates=0, out_of_order=0, longest_gap=0, bad_packets=0)


@pytest.mark.parametrize("port", [-1, 65536])
def test_e5_rejects_port_before_opening(tmp_path: Path, port: int) -> None:
    with pytest.raises(ValueError):
        capture_report(tmp_path / "does-not-exist.pcap", port)


@pytest.mark.parametrize("field,value", [
    pytest.param(None, 0, id="truncated-global-header"),
    pytest.param(16, 0, id="zero-snaplen"),
    pytest.param(16, 1, id="captured-length-exceeds-snaplen"),
    pytest.param(36, 1, id="captured-length-exceeds-original"),
])
def test_e5_file_errors_propagate(tmp_path: Path, field: int | None, value: int) -> None:
    with pytest.raises(FileNotFoundError):
        capture_report(tmp_path / "does-not-exist.pcap", 5005)
    path = tmp_path / "malformed.pcap"
    write_capture(path, [(5005, wire(10, []))])
    data = bytearray(path.read_bytes())
    if field is None:
        data = bytearray(b"broken")
    else:
        # Global snaplen is at byte 16; the first record's original length at 36.
        struct.pack_into("<I", data, field, value)
    path.write_bytes(data)
    with pytest.raises(ValueError):
        capture_report(path, 5005)


@pytest.fixture(params=["\n", "\r\n"], ids=["LF", "CRLF"])
def limits_csv(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    path = tmp_path / "limits.csv"
    lines = [
        "channel,value,low,high",
        "sense_A,3.1,3.2,3.4",
        "sense_B,5,4.9,5.1",
        "sense_A,3.5,3.2,3.4",
        "",
        '"temp,\u00b0C",-11,-10,20',
        '"temp,\u00b0C",21,-10,20',
        "sense_A,3.3,3.2,3.4",
        "sense_A,3.1,3.2,3.4",
    ]
    path.write_bytes((request.param.join(lines) + request.param).encode("utf-8"))
    return path


def test_e6_counts_failed_rows_by_channel(limits_csv: Path) -> None:
    original = limits_csv.read_bytes()
    got = limit_failures(limits_csv)
    assert got == {"sense_A": 3, "temp,\u00b0C": 2}, f"count only failures, including repeated rows: {got}"
    assert type(got) is dict, "return an ordinary dictionary"
    assert limits_csv.read_bytes() == original, "reading the log must not change it"


@pytest.mark.parametrize("value,low,high", [(3.2, 3.2, 3.4), (3.4, 3.2, 3.4), (5, 5, 5), (-2, -2, -1), (-1, -2, -1)])
def test_e6_inclusive_limits(tmp_path: Path, value: float, low: float, high: float) -> None:
    path = tmp_path / "boundary.csv"
    path.write_text(f"channel,value,low,high\nCH1,{value},{low},{high}\n", encoding="utf-8")
    assert limit_failures(path) == {}, "limit endpoints and equal limits pass"


@pytest.mark.parametrize("tail", ["", "\n\n", "CH1,1e-3,0,1\n\n"])
def test_e6_no_failing_rows(tmp_path: Path, tail: str) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("channel,value,low,high\n" + tail, encoding="utf-8")
    assert limit_failures(path) == {}, "header-only, blank lines, and passing rows produce no failures"


@pytest.mark.parametrize("row", ["CH2,FAULT,0,1", "CH2,0,BAD,1", "CH2,0,0,BAD"])
def test_e6_invalid_numbers_propagate(tmp_path: Path, row: str) -> None:
    path = tmp_path / "damaged.csv"
    path.write_text("channel,value,low,high\nCH1,2,0,1\n" + row + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        limit_failures(path)


@pytest.mark.parametrize("value", [0, 1, 2])
def test_e6_reversed_limits_rejected(tmp_path: Path, value: int) -> None:
    path = tmp_path / "reversed.csv"
    path.write_text(f"channel,value,low,high\nCH1,{value},2,0\n", encoding="utf-8")
    with pytest.raises(ValueError):
        limit_failures(path)


def test_e6_missing_file_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        limit_failures(tmp_path / "missing.csv")


class FakeMux:
    """A recording transport; disconnect always succeeds, as the contract promises."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.reply = "2.75"
        self.failure_on = ""
        self.failure: BaseException | None = None

    def write(self, command: str) -> None:
        self.calls.append(("write", command))
        if command.startswith("ROUT:CLOS") and self.failure_on == "select" and self.failure is not None:
            raise self.failure

    def query(self, command: str) -> str:
        self.calls.append(("query", command))
        if self.failure_on == "query" and self.failure is not None:
            raise self.failure
        return self.reply


@pytest.fixture
def mux() -> FakeMux:
    return FakeMux()


@pytest.mark.parametrize("channel,reply,expected", [(1, " 2.750\n", 2.75), (3, "+1.2E-3", 0.0012), (8, "-4.5", -4.5)])
def test_e7_select_read_disconnect(mux: FakeMux, channel: int, reply: str, expected: float) -> None:
    mux.reply = reply
    assert sample_mux(channel, mux.write, mux.query) == expected, "return the numeric meter reply"
    assert mux.calls == [("write", f"ROUT:CLOS (@{channel})"), ("query", "READ?"), ("write", "ROUT:OPEN:ALL")], "select, query once, then disconnect"


def test_e7_each_call_repeats_the_sequence(mux: FakeMux) -> None:
    assert sample_mux(2, mux.write, mux.query) == 2.75
    mux.reply = "0"
    assert sample_mux(2, mux.write, mux.query) == 0.0, "do not reuse a previous measurement"
    cycle = [("write", "ROUT:CLOS (@2)"), ("query", "READ?"), ("write", "ROUT:OPEN:ALL")]
    assert mux.calls == cycle * 2, "even the same channel must be selected and disconnected again"


@pytest.mark.parametrize("channel", [-1, 0, 9, 65535])
def test_e7_invalid_channel_sends_nothing(mux: FakeMux, channel: int) -> None:
    mux.calls.append(("write", "earlier command"))
    with pytest.raises(ValueError):
        sample_mux(channel, mux.write, mux.query)
    assert mux.calls == [("write", "earlier command")], "validate before entering the cleanup block"


@pytest.mark.parametrize("reply", ["", "NO READING"])
def test_e7_bad_numeric_reply_still_disconnects(mux: FakeMux, reply: str) -> None:
    mux.reply = reply
    with pytest.raises(ValueError):
        sample_mux(4, mux.write, mux.query)
    assert mux.calls == [("write", "ROUT:CLOS (@4)"), ("query", "READ?"), ("write", "ROUT:OPEN:ALL")], "conversion failure still requires disconnect"


@pytest.mark.parametrize("operation,error_type", [("select", OSError), ("query", TimeoutError), ("query", ConnectionError), ("query", KeyboardInterrupt)])
def test_e7_transport_failure_still_disconnects(mux: FakeMux, operation: str, error_type: type[BaseException]) -> None:
    error = error_type("station operation interrupted")
    mux.failure_on = operation
    mux.failure = error
    with pytest.raises(error_type) as caught:
        sample_mux(5, mux.write, mux.query)
    assert caught.value is error, "preserve the original error object"
    expected = [("write", "ROUT:CLOS (@5)")]
    if operation == "query":
        expected.append(("query", "READ?"))
    expected.append(("write", "ROUT:OPEN:ALL"))
    assert mux.calls == expected, "attempt cleanup once, even when channel selection fails"
