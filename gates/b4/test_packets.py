"""Packet layout and corruption checks, independent of the learner's encoder."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
import struct

import pytest


def test_packet_is_dataclass_with_contract_fields(telemetry):
    packet = telemetry.Packet(seq=12, timestamp_us=9000, readings={2: 5.0})
    assert is_dataclass(packet)
    assert [field.name for field in fields(packet)] == ["seq", "timestamp_us", "readings"]
    assert packet == telemetry.Packet(12, 9000, {2: 5.0})


def test_packet_fields_are_frozen(telemetry):
    packet = telemetry.Packet(12, 9000, {2: 5.0})
    for name, replacement in [("seq", 13), ("timestamp_us", 1), ("readings", {})]:
        with pytest.raises(FrozenInstanceError):
            setattr(packet, name, replacement)


def test_build_packet_uses_big_endian_sorted_channels_and_crc(telemetry, wire_packet):
    readings = {255: -2.5, 3: 24.125, 0: 0.0}
    data = telemetry.build_packet(0x1234, 0x0102030405060708, readings)
    assert isinstance(data, bytes)
    assert data == wire_packet(0x1234, 0x0102030405060708,
                               ((0, 0.0), (3, 24.125), (255, -2.5)))


def test_parse_packet_reads_independent_wire_bytes(telemetry, wire_packet):
    packet = telemetry.parse_packet(wire_packet(65535, 2**64 - 1, ((0, -1.5), (255, 30.0))))
    assert isinstance(packet, telemetry.Packet)
    assert packet == telemetry.Packet(65535, 2**64 - 1, {0: -1.5, 255: 30.0})


def test_empty_readings_and_zero_header_values_are_valid(telemetry, wire_packet):
    data = telemetry.build_packet(0, 0, {})
    assert data == wire_packet(0, 0, ())
    assert len(data) == 17
    assert telemetry.parse_packet(data) == telemetry.Packet(0, 0, {})


def test_maximum_reading_count_is_valid(telemetry, wire_packet):
    readings = {ch: float(ch) for ch in range(255)}
    data = telemetry.build_packet(65535, 1, readings)
    assert data == wire_packet(65535, 1, tuple(readings.items()))
    assert telemetry.parse_packet(data).readings == readings


def test_values_use_float32_rounding(telemetry, wire_packet):
    rounded = struct.unpack(">f", struct.pack(">f", 0.1))[0]
    assert telemetry.build_packet(1, 2, {4: 0.1}) == wire_packet(1, 2, ((4, 0.1),))
    assert telemetry.parse_packet(wire_packet(1, 2, ((4, 0.1),))).readings == {4: rounded}


@pytest.mark.parametrize("seq", [-1, 65536])
def test_build_packet_rejects_sequence_outside_u16(telemetry, seq):
    with pytest.raises(ValueError):
        telemetry.build_packet(seq, 0, {})


@pytest.mark.parametrize("channel", [-1, 256])
def test_build_packet_rejects_channel_outside_u8(telemetry, channel):
    with pytest.raises(ValueError):
        telemetry.build_packet(0, 0, {channel: 1.0})


def test_build_packet_rejects_more_than_255_readings(telemetry):
    with pytest.raises(ValueError):
        telemetry.build_packet(0, 0, {ch: 1.0 for ch in range(256)})


@pytest.mark.parametrize("data", [b"", b"\xeb\x90" + b"\x00" * 14], ids=["empty", "short"])
def test_parse_packet_rejects_short_data(telemetry, data):
    with pytest.raises(telemetry.PacketError):
        telemetry.parse_packet(data)


@pytest.mark.parametrize("variant", ["count-too-large", "count-too-small", "extra-byte"])
def test_parse_packet_rejects_length_disagreeing_with_count(telemetry, wire_packet, variant):
    if variant == "extra-byte":
        data = wire_packet() + b"\x00"
    else:
        data = wire_packet(count=2 if variant == "count-too-large" else 0)
    with pytest.raises(telemetry.PacketError):
        telemetry.parse_packet(data)


def test_parse_packet_rejects_bad_sync_with_valid_crc(telemetry, wire_packet):
    with pytest.raises(telemetry.PacketError):
        telemetry.parse_packet(wire_packet(sync=0x90EB))


@pytest.mark.parametrize("offset", [4, -1], ids=["body-corrupt", "crc-corrupt"])
def test_parse_packet_rejects_crc_mismatch(telemetry, wire_packet, offset):
    data = bytearray(wire_packet())
    data[offset] ^= 1
    with pytest.raises(telemetry.PacketError):
        telemetry.parse_packet(bytes(data))


def test_parse_packet_rejects_duplicate_channel_with_valid_crc(telemetry, wire_packet):
    with pytest.raises(telemetry.PacketError):
        telemetry.parse_packet(wire_packet(readings=((2, 1.0), (2, 2.0))))


def test_parse_packet_accepts_unsorted_unique_channels(telemetry, wire_packet):
    packet = telemetry.parse_packet(wire_packet(readings=((255, 2.0), (0, -1.0))))
    assert packet.readings == {255: 2.0, 0: -1.0}
