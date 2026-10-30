"""Offline station captures: all fixtures are deterministic and local."""
from io import BytesIO
from pathlib import Path
import struct
import zlib

import pytest

from starter.pcap import (
    iter_records, read_global_header, telemetry_from_capture, udp_payloads,
)

DATA = Path(__file__).resolve().parents[1] / "data/telemetry.pcap"


def global_header(order: str = "<", *, snaplen: int = 65535,
                  linktype: int = 1, version: tuple[int, int] = (2, 4)) -> bytes:
    return struct.pack(order + "IHHiiII", 0xA1B2C3D4, *version, -3600, 99,
                       snaplen, linktype)


def save_capture(tmp_path: Path, frames: list[bytes], order: str = "<") -> Path:
    raw = global_header(order)
    for index, frame in enumerate(frames):
        raw += struct.pack(order + "IIII", 10 + index, 250000, len(frame), len(frame))
        raw += frame
    path = tmp_path / "station capture.pcap"
    path.write_bytes(raw)
    return path


def network_frame(payload: bytes, *, port: int = 5005, source: int = 1234,
                  ihl: int = 5, flags: int = 0x4000, protocol: int = 17) -> bytes:
    udp = struct.pack(">HHHH", source, port, 8 + len(payload), 0) + payload
    ip = bytearray(ihl * 4)
    ip[0] = 0x40 | ihl
    ip[2:4] = struct.pack(">H", len(ip) + len(udp))
    ip[6:8] = struct.pack(">H", flags)
    ip[9] = protocol
    if ihl > 5:
        ip[20:] = b"\x01" * (len(ip) - 20)
    return b"\x02" * 12 + b"\x08\x00" + bytes(ip) + udp


def packet(seq: int, channels: list[int], *, sync: int = 0xEB90) -> bytes:
    body = struct.pack(">HHQB", sync, seq, 987654321, len(channels))
    body += b"".join(struct.pack(">Bf", channel, 2.5) for channel in channels)
    return body + struct.pack(">I", zlib.crc32(body))


def with_crc(body: bytes) -> bytes:
    return body + struct.pack(">I", zlib.crc32(body))


def replace_bytes(raw: bytes, offset: int, value: bytes) -> bytes:
    return raw[:offset] + value + raw[offset + len(value):]


@pytest.mark.parametrize("order", ["<", ">"])
@pytest.mark.parametrize("snaplen,linktype", [(65535, 1), (96, 101)])
def test_e1_header_fields(order: str, snaplen: int, linktype: int) -> None:
    got = read_global_header(BytesIO(global_header(order, snaplen=snaplen,
                                                  linktype=linktype)))
    expected = {"byteorder": order, "version_major": 2, "version_minor": 4,
                "snaplen": snaplen, "linktype": linktype}
    assert got == expected, f"capture header should decode to {expected}, got {got}"


def test_e1_reads_current_position_without_closing() -> None:
    stream = BytesIO(b"prefix" + global_header() + b"next record")
    stream.seek(6)
    read_global_header(stream)
    assert not stream.closed, "the caller owns the open capture file"
    assert stream.tell() == 30, "consume only the 24-byte global header"
    assert stream.read() == b"next record"


@pytest.mark.parametrize("magic", [b"BAD!", bytes.fromhex("4d3cb2a1"),
                                    bytes.fromhex("a1b23c4d"), bytes.fromhex("0a0d0d0a")])
def test_e1_rejects_unsupported_magic(magic: bytes) -> None:
    with pytest.raises(ValueError):
        read_global_header(BytesIO(magic + global_header()[4:]))


@pytest.mark.parametrize("raw", [b"", global_header()[:23],
                                  global_header(version=(2, 3)),
                                  global_header(version=(3, 4)),
                                  global_header(snaplen=0)])
def test_e1_rejects_incomplete_or_invalid_header(raw: bytes) -> None:
    with pytest.raises(ValueError):
        read_global_header(BytesIO(raw))


@pytest.mark.parametrize("order", ["<", ">"])
def test_e2_record_bytes_timestamps_and_original_length(tmp_path: Path, order: str) -> None:
    path = tmp_path / "trimmed.pcap"
    path.write_bytes(global_header(order, linktype=101)
                     + struct.pack(order + "IIII", 10, 250000, 3, 200) + b"abc"
                     + struct.pack(order + "IIII", 11, 1, 0, 0)
                     + struct.pack(order + "IIII", 12, 999999, 2, 2) + b"\x00\xff")
    got = list(iter_records(str(path)))
    assert got == [(10.25, b"abc"), (11.000001, b""), (12.999999, b"\x00\xff")], (
        "read captured length, retain empty frames, and scale microseconds")


def test_e2_empty_and_supplied_capture(tmp_path: Path) -> None:
    empty = save_capture(tmp_path, [])
    assert list(iter_records(empty)) == [], "a header-only capture has no records"
    records = list(iter_records(DATA))
    assert len(records) == 7, "the station fixture contains seven frames"
    assert [timestamp for timestamp, _ in records] == [1700000000.25 + i for i in range(7)]
    assert all(isinstance(frame, bytes) and len(frame) >= 60 for _, frame in records)


@pytest.mark.parametrize("tail", [b"\x00", b"\x00" * 15,
    struct.pack("<IIII", 1, 0, 5, 5) + b"short"[:4],
    struct.pack("<IIII", 1, 1000000, 0, 0),
    struct.pack("<IIII", 1, 0, 65536, 65536),
    struct.pack("<IIII", 1, 0, 3, 2) + b"abc"])
def test_e2_rejects_broken_records(tmp_path: Path, tail: bytes) -> None:
    path = tmp_path / "broken.pcap"
    path.write_bytes(global_header() + tail)
    with pytest.raises(ValueError):
        list(iter_records(path))


def test_e2_yields_before_later_truncation(tmp_path: Path) -> None:
    path = save_capture(tmp_path, [b"first"])
    path.write_bytes(path.read_bytes() + b"broken")
    records = iter_records(path)
    assert iter(records) is records, "return an iterator of records"
    assert next(records) == (10.25, b"first"), "do not read later records before yielding"
    with pytest.raises(ValueError):
        next(records)


def test_e2_propagates_header_errors(tmp_path: Path) -> None:
    path = tmp_path / "not pcap"
    path.write_bytes(b"garbage")
    with pytest.raises(ValueError):
        list(iter_records(path))

@pytest.mark.parametrize("order", ["<", ">"])
@pytest.mark.parametrize("ihl", [5, 6, 15])
def test_e3_options_padding_filter_and_order(tmp_path: Path, order: str, ihl: int) -> None:
    wanted = network_frame(b"measurement", ihl=ihl)
    path = save_capture(tmp_path, [wanted + b"Ethernet padding",
        network_frame(b"wrong destination", port=6006, source=5005),
        network_frame(b"second"), wanted], order)
    assert udp_payloads(path, 5005) == [b"measurement", b"second", b"measurement"], (
        "follow IHL, select destination port, omit padding, retain duplicates")


@pytest.mark.parametrize("port", [0, 65535])
def test_e3_empty_payload_and_ip_tail(tmp_path: Path, port: int) -> None:
    frame = network_frame(b"tail", port=port)
    # IP contains four bytes after an empty UDP datagram; they are not payload.
    frame = replace_bytes(frame, 14 + 20 + 4, struct.pack(">H", 8))
    path = save_capture(tmp_path, [frame])
    assert udp_payloads(str(path), port) == [b""], "respect UDP's declared end"


BASE = network_frame(b"sample")
BAD_FRAMES = [
    pytest.param(b"", id="empty-frame"),
    pytest.param(BASE[:13], id="short-ethernet"),
    pytest.param(BASE[:33], id="short-ip"),
    pytest.param(BASE[:41], id="short-udp"),
    pytest.param(replace_bytes(BASE, 12, b"\x08\x06"), id="arp"),
    pytest.param(replace_bytes(BASE, 12, b"\x86\xdd"), id="ipv6"),
    pytest.param(replace_bytes(BASE, 12, b"\x81\x00"), id="vlan"),
    pytest.param(replace_bytes(BASE, 14, b"\x65"), id="wrong-ip-version"),
    pytest.param(replace_bytes(BASE, 14, b"\x44"), id="ihl-too-small"),
    pytest.param(replace_bytes(BASE, 14, b"\x4f"), id="truncated-options"),
    pytest.param(replace_bytes(BASE, 16, struct.pack(">H", 27)), id="ip-too-short"),
    pytest.param(replace_bytes(BASE, 16, struct.pack(">H", 100)), id="ip-truncated"),
    pytest.param(replace_bytes(BASE, 23, b"\x06"), id="tcp"),
    pytest.param(replace_bytes(BASE, 20, b"\x20\x00"), id="more-fragments"),
    pytest.param(replace_bytes(BASE, 20, b"\x00\x01"), id="fragment-offset"),
    pytest.param(replace_bytes(BASE, 38, struct.pack(">H", 7)), id="udp-too-short"),
    pytest.param(replace_bytes(BASE, 38, struct.pack(">H", 99)), id="udp-truncated"),
]


@pytest.mark.parametrize("bad", BAD_FRAMES)
def test_e3_skips_bad_or_unrelated_frames(tmp_path: Path, bad: bytes) -> None:
    path = save_capture(tmp_path, [bad, network_frame(b"still usable")])
    assert udp_payloads(path, 5005) == [b"still usable"], (
        "skip an unusable frame and continue to the next instrument message")


def test_e3_supplied_capture_and_no_matches() -> None:
    payloads = udp_payloads(DATA, 5005)
    assert len(payloads) == 4, "UDP extraction retains bad application CRCs for E4"
    assert [int.from_bytes(raw[2:4], "big") for raw in payloads] == [40, 41, 42, 43]
    assert udp_payloads(DATA, 54321) == [], "no destination matches returns an empty list"


@pytest.mark.parametrize("port", [-1, 65536])
def test_e3_rejects_invalid_port(port: int) -> None:
    with pytest.raises(ValueError):
        udp_payloads(DATA, port)


def test_e3_propagates_pcap_error(tmp_path: Path) -> None:
    path = tmp_path / "incomplete.pcap"
    path.write_bytes(global_header() + b"partial")
    with pytest.raises(ValueError):
        udp_payloads(path, 5005)


def test_e4_supplied_capture() -> None:
    assert telemetry_from_capture(DATA, 5005) == [(40, 2), (42, 0), (43, 1)], (
        "exclude damaged sequence 41, retain zero-channel and IP-options packets")
    assert telemetry_from_capture(DATA, 54321) == [], "no packets means no summaries"


@pytest.mark.parametrize("order", ["<", ">"])
def test_e4_counts_order_duplicates_and_port(tmp_path: Path, order: str) -> None:
    entries = [(65535, [8, 2]), (0, []), (9, list(range(255))), (65535, [8, 2])]
    frames = [network_frame(packet(seq, channels)) for seq, channels in entries]
    frames.insert(1, network_frame(packet(123, [4]), port=6006))
    path = save_capture(tmp_path, frames, order)
    assert telemetry_from_capture(str(path), 5005) == [(65535, 2), (0, 0), (9, 255), (65535, 2)], (
        "report channel counts, accept unsorted unique channels, preserve capture order")


GOOD = packet(10, [1, 3])
BAD_PACKETS = [
    pytest.param(b"", id="empty"),
    pytest.param(GOOD[:12], id="short-header"),
    pytest.param(GOOD[:16], id="short-minimum"),
    pytest.param(packet(10, [1], sync=0), id="bad-sync-valid-crc"),
    pytest.param(with_crc(replace_bytes(GOOD[:-4], 12, b"\x03")), id="count-too-large"),
    pytest.param(with_crc(replace_bytes(GOOD[:-4], 12, b"\x01")), id="count-too-small"),
    pytest.param(GOOD[:-1], id="truncated-crc"),
    pytest.param(with_crc(GOOD[:-4] + b"extra"), id="trailing-data"),
    pytest.param(replace_bytes(GOOD, 14, bytes([GOOD[14] ^ 1])), id="corrupt-reading"),
    pytest.param(replace_bytes(GOOD, 2, b"\x00\x0b"), id="corrupt-sequence"),
    pytest.param(GOOD[:-4] + b"\x00" * 4, id="bad-crc"),
    pytest.param(packet(10, [7, 7]), id="duplicate-channel-valid-crc"),
]


@pytest.mark.parametrize("bad", BAD_PACKETS)
def test_e4_skips_invalid_telemetry_and_continues(tmp_path: Path, bad: bytes) -> None:
    path = save_capture(tmp_path, [network_frame(bad), network_frame(packet(11, [5]))])
    assert telemetry_from_capture(path, 5005) == [(11, 1)], (
        "bad application packets must not hide subsequent valid measurements")


def test_e4_propagates_file_and_port_errors(tmp_path: Path) -> None:
    path = tmp_path / "broken.pcap"
    path.write_bytes(global_header() + b"broken")
    with pytest.raises(ValueError):
        telemetry_from_capture(path, 5005)
    with pytest.raises(ValueError):
        telemetry_from_capture(DATA, -1)
