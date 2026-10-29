import pytest

from starter.registers import clear_bits, decode_status, explain, field, set_bits, unpack_status_frame
from starter.registers import endian_answers


_ENDIAN_ANSWERS = {"Q1": "B", "Q2": "D", "Q3": "A", "Q4": "C"}

@pytest.mark.parametrize(
    ("byte", "expected"),
    [
        (0, {"ready": False, "output_on": False, "overcurrent": False, "overtemp": False}),
        (255, {"ready": True, "output_on": True, "overcurrent": True, "overtemp": True}),
        (0x85, {"ready": True, "output_on": True, "overcurrent": False, "overtemp": True}),
    ],
)
def test_e1_operator_flags(byte: int, expected: dict[str, bool]) -> None:
    got = decode_status(byte)
    assert got == expected, f"status {byte:#04x}: expected {expected}, got {got}"
    assert all(type(value) is bool for value in got.values()), "operator flags must be bool values"


@pytest.mark.parametrize("bit, active", [(0, "ready"), (2, "output_on"), (4, "overcurrent"), (7, "overtemp")])
def test_e1_individual_masks(bit: int, active: str) -> None:
    got = decode_status(1 << bit)
    expected = {name: name == active for name in ("ready", "output_on", "overcurrent", "overtemp")}
    assert got == expected, f"bit {bit} alone should activate only {active}"


def test_e1_reserved_bits_are_ignored() -> None:
    got = decode_status(0x6A)
    expected = {"ready": False, "output_on": False, "overcurrent": False, "overtemp": False}
    assert got == expected, "reserved bits must not become status flags"


@pytest.mark.parametrize("byte", [-1, 256, 1024])
def test_e1_invalid_byte(byte: int) -> None:
    with pytest.raises(ValueError):
        decode_status(byte)


@pytest.mark.parametrize("reg, mask, expected", [(0x20, 0x03, 0x23), (0x85, 0x14, 0x95), (0xA5, 0, 0xA5), (0, 255, 255), (255, 255, 255)])
def test_e2_set_selected_bits(reg: int, mask: int, expected: int) -> None:
    got = set_bits(reg, mask)
    assert got == expected, f"set {mask:#04x} in {reg:#04x}: expected {expected:#04x}, got {got:#04x}"


@pytest.mark.parametrize("reg, mask, expected", [(0x23, 0x03, 0x20), (0x95, 0x14, 0x81), (0xA5, 0, 0xA5), (255, 255, 0), (0, 255, 0)])
def test_e2_clear_selected_bits(reg: int, mask: int, expected: int) -> None:
    got = clear_bits(reg, mask)
    assert got == expected, f"clear {mask:#04x} in {reg:#04x}: expected {expected:#04x}, got {got:#04x}"


@pytest.mark.parametrize("reg, shift, width, expected", [(0xD7, 4, 3, 5), (0xAC, 2, 3, 3), (255, 0, 8, 255), (128, 7, 1, 1), (0, 0, 1, 0), (0xF0, 0, 4, 0)])
def test_e2_extract_unsigned_field(reg: int, shift: int, width: int, expected: int) -> None:
    got = field(reg, shift, width)
    assert got == expected, f"register {reg:#04x}, shift {shift}, width {width}: expected {expected}, got {got}"


@pytest.mark.parametrize("reg, mask", [(-1, 0), (256, 0), (0, -1), (0, 256)])
@pytest.mark.parametrize("operation", [set_bits, clear_bits])
def test_e2_invalid_bit_operands(operation, reg: int, mask: int) -> None:
    with pytest.raises(ValueError):
        operation(reg, mask)


@pytest.mark.parametrize("reg, shift, width", [(-1, 0, 1), (256, 0, 1), (0, -1, 1), (0, 8, 1), (0, 0, 0), (0, 0, -1), (0, 0, 9), (0, 7, 2)])
def test_e2_invalid_field_ranges(reg: int, shift: int, width: int) -> None:
    with pytest.raises(ValueError):
        field(reg, shift, width)


def test_e2_configuration_round_trip() -> None:
    configured = set_bits(clear_bits(0x8B, 0x70), 0x50)
    assert configured == 0xDB, "updating range must preserve unrelated configuration bits"
    assert field(configured, 4, 3) == 5, "header's range field should contain the chosen range"


@pytest.mark.parametrize(
    "payload, expected",
    [
        (b"\x01\xe0\x2e\xfa\x00\x02\x00", {"status": 1, "voltage_mv": 12000, "current_ma": 250, "sequence": 2}),
        (b"\x6a\x34\x12\x78\x56\xbc\x9a", {"status": 106, "voltage_mv": 4660, "current_ma": 22136, "sequence": 39612}),
    ],
)
def test_e3_packed_offsets_and_byte_order(payload: bytes, expected: dict[str, int]) -> None:
    got = unpack_status_frame(payload)
    assert got == expected, f"frame {payload.hex()}: expected {expected}, got {got}"
    assert all(type(value) is int for value in got.values()), "frame fields must remain raw integers"


@pytest.mark.parametrize("raw_current, expected", [(b"\xff\xff", -1), (b"\x00\x80", -32768), (b"\xff\x7f", 32767), (b"\x06\xff", -250)])
def test_e3_signed_current(raw_current: bytes, expected: int) -> None:
    payload = b"\x80\x01\x00" + raw_current + b"\x01\x00"
    got = unpack_status_frame(payload)
    assert got == {"status": 128, "voltage_mv": 1, "current_ma": expected, "sequence": 1}, "current signedness must not affect neighboring members"


@pytest.mark.parametrize(
    "payload, expected",
    [
        (b"\x00" * 7, {"status": 0, "voltage_mv": 0, "current_ma": 0, "sequence": 0}),
        (b"\xff" * 7, {"status": 255, "voltage_mv": 65535, "current_ma": -1, "sequence": 65535}),
    ],
)
def test_e3_full_member_ranges(payload: bytes, expected: dict[str, int]) -> None:
    got = unpack_status_frame(payload)
    assert got == expected, "preserve raw status bits, units, and the full unsigned counter range"


@pytest.mark.parametrize("size", [0, 1, 6, 8, 10])
def test_e3_reject_wrong_frame_length(size: int) -> None:
    with pytest.raises(ValueError):
        unpack_status_frame(bytes(size))


@pytest.mark.parametrize(
    "line, expected",
    [
        ("value = *status_ptr;", "Read the byte that status_ptr points to into value."),
        ("*status_ptr = 0;", "Write zero to the byte that status_ptr points to."),
    ],
)
def test_e4_pointer_read_and_write(line: str, expected: str) -> None:
    got = explain(line)
    assert got == expected, f"for {line!r}, use the exact matching meaning: {expected!r}"


@pytest.mark.parametrize(
    "line, expected",
    [
        ("value = frame_ptr->voltage_mv;", "Read the voltage_mv member of the status frame that frame_ptr points to into value."),
        ("value = (uint8_t)raw;", "Convert raw to an unsigned 8-bit integer, keeping its lowest 8 bits, and store it in value."),
        ("value = *status_reg;", "Read the volatile hardware byte that status_reg points to into value."),
    ],
)
def test_e4_member_cast_and_volatile_read(line: str, expected: str) -> None:
    got = explain(line)
    assert got == expected, f"for {line!r}, use the exact matching meaning: {expected!r}"


@pytest.mark.parametrize("line", ["", "value = status_ptr;", " value = *status_ptr;", "value = *status_reg;\n"])
def test_e4_reject_unknown_lines(line: str) -> None:
    with pytest.raises(ValueError):
        explain(line)


def test_e5_q1_big_endian_memory() -> None:
    answers = endian_answers()
    assert isinstance(answers, dict), "E5: Return a dictionary as described in the README"
    assert set(answers) == {"Q1", "Q2", "Q3", "Q4"}, "E5: Return exactly the four question IDs"
    correct = answers.get("Q1") == _ENDIAN_ANSWERS["Q1"]
    assert correct, "Q1: Reread Endianness, Overview, and compare the byte positions"


def test_e5_q2_network_byte_order() -> None:
    correct = endian_answers().get("Q2") == _ENDIAN_ANSWERS["Q2"]
    assert correct, "Q2: Reread Endianness, Networking, for the agreed network convention"


def test_e5_q3_test_pc_native_order() -> None:
    correct = endian_answers().get("Q3") == _ENDIAN_ANSWERS["Q3"]
    assert correct, "Q3: Reread Endianness, Hardware, for x86 and ARM byte order"


def test_e5_q4_wrong_unpack_order() -> None:
    correct = endian_answers().get("Q4") == _ENDIAN_ANSWERS["Q4"]
    assert correct, "Q4: Reread Endianness, Overview, and the README's worked struct example"
