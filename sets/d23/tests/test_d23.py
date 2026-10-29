"""Station packet checks use independent wire bytes, not learner encoders."""

import math
import struct
import zlib

import pytest

from starter.packets import (
    PacketError,
    build_packet,
    find_packets,
    pack_header,
    parse_packet,
    unpack_header,
)


def _with_crc(body: bytes) -> bytes:
    return body + zlib.crc32(body).to_bytes(4, "big")


def _wire(seq: int, ts_us: int, readings: list[tuple[int, float]]) -> bytes:
    # Keep channel order and duplicates: malformed input must reach the parser.
    header = (
        b"\xeb\x90" + seq.to_bytes(2, "big") + ts_us.to_bytes(8, "big")
        + len(readings).to_bytes(1, "big")
    )
    payload = b"".join(bytes([channel]) + struct.pack(">f", value) for channel, value in readings)
    return _with_crc(header + payload)


@pytest.fixture
def station_packet() -> bytes:
    # seq=1, timestamp=2, channel=3, value=1.5; literal header and payload.
    return _with_crc(bytes.fromhex("eb900001000000000000000201033fc00000"))


@pytest.mark.parametrize(
    "seq,ts_us,count,expected",
    [
        (0, 0, 0, b"\xeb\x90" + b"\x00" * 11),
        (65535, 2**64 - 1, 255, b"\xeb\x90" + b"\xff" * 11),
        (0x1234, 0x0102030405060708, 3, bytes.fromhex("eb901234010203040506070803")),
    ],
)
def test_e1_header_wire_bytes(seq: int, ts_us: int, count: int, expected: bytes) -> None:
    got = pack_header(seq, ts_us, count)
    assert isinstance(got, bytes), "pack_header must return bytes"
    assert got == expected, f"header must have exact big-endian bytes: {got.hex()}"


@pytest.mark.parametrize(
    "wire,expected",
    [
        (b"\xeb\x90" + b"\x00" * 11, (0, 0, 0)),
        (b"\xeb\x90" + b"\xff" * 11, (65535, 2**64 - 1, 255)),
        (bytes.fromhex("eb901234010203040506070803"), (0x1234, 0x0102030405060708, 3)),
    ],
)
def test_e1_unpack_independent_header(wire: bytes, expected: tuple[int, int, int]) -> None:
    got = unpack_header(wire)
    assert isinstance(got, tuple), "unpack_header must return a tuple"
    assert got == expected, f"unpacked header expected {expected}, got {got}"


@pytest.mark.parametrize(
    "seq,ts_us,count",
    [(-1, 0, 0), (65536, 0, 0), (0, -1, 0), (0, 2**64, 0), (0, 0, -1), (0, 0, 256)],
)
def test_e1_reject_header_range(seq: int, ts_us: int, count: int) -> None:
    with pytest.raises(ValueError):
        pack_header(seq, ts_us, count)


@pytest.mark.parametrize("size", [*range(13), 14, 17, 40])
def test_e1_reject_header_length(size: int) -> None:
    with pytest.raises(PacketError):
        unpack_header((b"\xeb\x90" + b"\x00" * 40)[:size])


@pytest.mark.parametrize("sync", [b"\x90\xeb", b"\x00\x00", b"\xeb\x91"])
def test_e1_reject_header_sync(sync: bytes) -> None:
    with pytest.raises(PacketError):
        unpack_header(sync + b"\x00" * 11)


def test_e2_exact_packet_and_crc(station_packet: bytes) -> None:
    got = build_packet(1, 2, {3: 1.5})
    assert isinstance(got, bytes), "the transmitter needs a bytes packet"
    assert got == station_packet, "header, reading, or big-endian CRC bytes disagree"


def test_e2_sorted_channels_and_input_unchanged() -> None:
    readings = {255: -2.25, 7: 1.5, 0: 0.1}
    before = list(readings.items())
    expected = _wire(12, 0x0102030405060708, [(0, 0.1), (7, 1.5), (255, -2.25)])
    got = build_packet(12, 0x0102030405060708, readings)
    assert got == expected, "emit ascending channels and preserve f32 precision"
    assert list(readings.items()) == before, "building must not modify the input dictionary"


@pytest.mark.parametrize("count", [0, 255])
def test_e2_reading_count_boundaries(count: int) -> None:
    pairs = [(channel, channel / 2.0) for channel in range(count)]
    got = build_packet(65535, 2**64 - 1, dict(pairs))
    assert got == _wire(65535, 2**64 - 1, pairs), f"failed at {count} readings"
    assert len(got) == 17 + 5 * count, "unexpected packet size or padding"


@pytest.mark.parametrize("seq,ts_us", [(-1, 0), (65536, 0), (0, -1), (0, 2**64)])
def test_e2_reject_header_range(seq: int, ts_us: int) -> None:
    with pytest.raises(ValueError):
        build_packet(seq, ts_us, {})


@pytest.mark.parametrize("channel", [-1, 256])
def test_e2_reject_channel_range(channel: int) -> None:
    with pytest.raises(ValueError):
        build_packet(1, 2, {channel: 1.0})


def test_e2_reject_too_many_readings() -> None:
    with pytest.raises(ValueError):
        build_packet(1, 2, {channel: 1.0 for channel in range(256)})

@pytest.mark.parametrize(
    "seq,ts_us,pairs",
    [
        (0, 0, []),
        (65535, 2**64 - 1, [(255, -2.25), (0, 0.1), (7, 1.5)]),
        (3, 1000, [(channel, channel / 2.0) for channel in range(255)]),
        (4, 2000, [(0, float("nan")), (1, float("inf")), (2, float("-inf"))]),
    ],
)
def test_e3_decode_independent_packets(seq: int, ts_us: int, pairs: list[tuple[int, float]]) -> None:
    got = parse_packet(_wire(seq, ts_us, pairs))
    assert isinstance(got, tuple), "parse_packet must return a tuple"
    got_seq, got_ts, readings = got
    assert (got_seq, got_ts) == (seq, ts_us), "sequence or timestamp changed"
    assert isinstance(readings, dict), "readings must be a channel-to-value dictionary"
    assert set(readings) == {channel for channel, _ in pairs}, "channel identifiers changed"
    for channel, value in pairs:
        (expected,) = struct.unpack(">f", struct.pack(">f", value))
        if math.isnan(expected):
            assert math.isnan(readings[channel]), "preserve a decoded NaN value"
        else:
            assert readings[channel] == expected, f"wrong decoded f32 for channel {channel}"


def test_e3_decode_literal_packet(station_packet: bytes) -> None:
    got = parse_packet(station_packet)
    assert got == (1, 2, {3: 1.5}), f"literal station packet decoded as {got}"


@pytest.mark.parametrize("size", range(17))
def test_e3_reject_short_data(station_packet: bytes, size: int) -> None:
    with pytest.raises(PacketError):
        parse_packet(station_packet[:size])


@pytest.mark.parametrize("damage", ["sync", "count_low", "count_high", "truncated", "extra", "little_crc"])
def test_e3_reject_sync_length_and_crc_order(station_packet: bytes, damage: str) -> None:
    body = bytearray(station_packet[:-4])
    if damage == "sync":
        body[:2] = b"\x90\xeb"
        bad = _with_crc(bytes(body))
    elif damage == "count_low":
        body[12] = 0
        bad = _with_crc(bytes(body))
    elif damage == "count_high":
        body[12] = 2
        bad = _with_crc(bytes(body))
    elif damage == "truncated":
        bad = station_packet[:-1]
    elif damage == "extra":
        bad = station_packet + b"\x00"
    else:
        bad = station_packet[:-4] + station_packet[-4:][::-1]
    with pytest.raises(PacketError):
        parse_packet(bad)


@pytest.mark.parametrize("offset", [2, 4, 11, 13, 14, 17, 18, 21])
def test_e3_reject_crc_damage(station_packet: bytes, offset: int) -> None:
    damaged = bytearray(station_packet)
    damaged[offset] ^= 1
    with pytest.raises(PacketError):
        parse_packet(bytes(damaged))


@pytest.mark.parametrize("pairs", [[(1, 1.5), (1, 2.5)], [(255, 1.0), (0, 2.0), (255, 3.0)]])
def test_e3_reject_duplicate_channels(pairs: list[tuple[int, float]]) -> None:
    with pytest.raises(PacketError):
        parse_packet(_wire(1, 2, pairs))


def test_e4_recover_junk_adjacent_and_repeated_packets(station_packet: bytes) -> None:
    empty = _wire(0, 0, [])
    large = _wire(65535, 2**64 - 1, [(channel, float(channel)) for channel in range(255)])
    stream = b"operator log\x00" + station_packet + empty + b"junk" + large + station_packet + b"tail\xeb"
    got = find_packets(stream)
    assert got == [station_packet, empty, large, station_packet], "preserve complete packets and stream order"
    assert all(isinstance(packet, bytes) for packet in got), "return original packet bytes"


@pytest.mark.parametrize("stream", [b"", b"junk", b"\xeb", b"\xeb\x90", b"\x90\xeb" * 6, b"\xeb\x90" + b"\x00" * 11])
def test_e4_no_complete_valid_packet(stream: bytes) -> None:
    assert find_packets(stream) == [], "junk and incomplete packets must be ignored"


def test_e4_skip_crc_damage_and_duplicate_channels(station_packet: bytes) -> None:
    damaged = bytearray(station_packet)
    damaged[-1] ^= 1
    duplicate = _wire(8, 9, [(2, 1.0), (2, 1.0)])
    stream = bytes(damaged) + duplicate + station_packet + bytes(damaged)
    assert find_packets(stream) == [station_packet], "reject both CRC damage and CRC-valid duplicate channels"


def test_e4_resync_inside_rejected_complete_candidate(station_packet: bytes) -> None:
    # count=4 claims 37 bytes. The real packet begins within that bad candidate.
    false_header = b"\xeb\x90" + b"\x00" * 10 + b"\x04"
    stream = false_header + station_packet + b"\x00" * 8
    assert find_packets(stream) == [station_packet], "advance one byte after rejection, not the claimed length"


def test_e4_resync_after_incomplete_candidate_and_overlapping_sync(station_packet: bytes) -> None:
    false_header = b"\xeb\x90" + b"\x00" * 10 + b"\xff"
    stream = false_header + b"junk\xeb" + station_packet + station_packet[:15]
    assert find_packets(stream) == [station_packet], "a damaged large count must not hide later packets"


def test_e4_keep_accepted_packet_with_sync_in_payload() -> None:
    (value_with_sync,) = struct.unpack(">f", b"\xeb\x90\x00\x00")
    packet = _wire(10, 20, [(1, value_with_sync), (2, 1.0)])
    assert find_packets(packet + packet) == [packet, packet], "sync may occur inside a valid reading"
