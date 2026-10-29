import math

import pytest

from starter.replies import format_setpoint, parse_idn, parse_reading, split_channels


def test_e1_instrument_identification() -> None:
    reply = "KEYSIGHT TECHNOLOGIES,34461A,MY57212345,A.03.01\n"
    expected = {
        "manufacturer": "KEYSIGHT TECHNOLOGIES",
        "model": "34461A",
        "serial": "MY57212345",
        "firmware": "A.03.01",
    }
    got = parse_idn(reply)
    assert got == expected, f"for identification {reply!r} expected {expected!r}, got {got!r}"


def test_e1_strips_each_field_preserving_internal_spaces() -> None:
    reply = " \tBench  Instruments , M 2 , SN007 , v1.0 \r\n"
    expected = {
        "manufacturer": "Bench  Instruments",
        "model": "M 2",
        "serial": "SN007",
        "firmware": "v1.0",
    }
    got = parse_idn(reply)
    assert got == expected, f"strip field edges only: expected {expected!r}, got {got!r}"


def test_e1_empty_fields_are_still_fields() -> None:
    got = parse_idn(", ,SERIAL,")
    expected = {"manufacturer": "", "model": "", "serial": "SERIAL", "firmware": ""}
    assert got == expected, f"four fields may contain empty strings: got {got!r}"


@pytest.mark.parametrize("reply", ["", "M", "M,MODEL,SERIAL", "M,MODEL,SERIAL,FW,EXTRA", ",,,,"])
def test_e1_rejects_wrong_field_count(reply: str) -> None:
    with pytest.raises(ValueError):
        parse_idn(reply)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("+1.23456789E+00", 1.23456789), ("-4.5e-3\r\n", -0.0045),
     (" 12 ", 12.0), ("\t0\n", 0.0), (".5", 0.5), ("1e-12", 1e-12)],
)
def test_e2_converts_numeric_replies(text: str, expected: float) -> None:
    got = parse_reading(text)
    assert isinstance(got, float), f"expected a float reading, got {type(got).__name__}"
    assert got == expected, f"for reading {text!r} expected {expected}, got {got}"


@pytest.mark.parametrize("text", ["9.9E+37", "+9.90000000E+37", " 9.90e37\r\n"])
def test_e2_overload_is_positive_infinity(text: str) -> None:
    got = parse_reading(text)
    assert got == math.inf, f"overload reply {text!r} must become positive infinity, got {got}"


@pytest.mark.parametrize("text", ["-9.9E+37", "9.8E+37", "1E+38"])
def test_e2_does_not_treat_other_large_values_as_overload(text: str) -> None:
    got = parse_reading(text)
    assert got == float(text), f"only positive 9.9e37 is the overload marker: got {got} for {text!r}"


@pytest.mark.parametrize("text", ["", " \t\r\n", "READY", "12 V", "1,2", "--4", "1e", "1 2"])
def test_e2_rejects_empty_or_garbage(text: str) -> None:
    with pytest.raises(ValueError):
        parse_reading(text)


@pytest.mark.parametrize(
    ("volts", "expected"),
    [(5.0, "VOLT 5.000"), (12.3456, "VOLT 12.346"),
     (1.2344, "VOLT 1.234"), (0.0001, "VOLT 0.000")],
)
def test_e3_formats_station_command(volts: float, expected: str) -> None:
    got = format_setpoint(volts)
    assert got == expected, f"for setpoint {volts} expected {expected!r}, got {got!r}"


@pytest.mark.parametrize(
    ("volts", "expected"), [(0.0, "VOLT 0.000"), (30.0, "VOLT 30.000"), (-0.0, "VOLT -0.000")]
)
def test_e3_accepts_inclusive_limits(volts: float, expected: str) -> None:
    got = format_setpoint(volts)
    assert got == expected, f"limit {volts} is allowed: expected {expected!r}, got {got!r}"


@pytest.mark.parametrize("volts", [-0.0001, 30.0001, -5.0, 100.0])
def test_e3_rejects_out_of_range_before_rounding(volts: float) -> None:
    with pytest.raises(ValueError):
        format_setpoint(volts)


@pytest.mark.parametrize("volts", [math.inf, -math.inf, math.nan])
def test_e3_rejects_nonfinite_setpoints(volts: float) -> None:
    with pytest.raises(ValueError):
        format_setpoint(volts)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("(@1,3,5)", [1, 3, 5]), ("(@12)", [12]), ("(@007,2)", [7, 2])],
)
def test_e4_individual_channels(text: str, expected: list[int]) -> None:
    got = split_channels(text)
    assert got == expected, f"for channel list {text!r} expected {expected}, got {got}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [("(@1:4)", [1, 2, 3, 4]), ("(@1,4:6)", [1, 4, 5, 6]),
     ("(@3:3,7:8)", [3, 7, 8])],
)
def test_e4_expands_inclusive_ranges(text: str, expected: list[int]) -> None:
    got = split_channels(text)
    assert got == expected, f"expand both range endpoints in {text!r}: expected {expected}, got {got}"


def test_e4_accepts_whitespace_at_token_edges() -> None:
    text = " \t(@ 1 , 4 : 6 )\r\n"
    got = split_channels(text)
    assert got == [1, 4, 5, 6], f"whitespace around numbers and the whole list is allowed: got {got}"


def test_e4_preserves_order_and_repeated_channels() -> None:
    got = split_channels("(@5,1:3,2,5)")
    assert got == [5, 1, 2, 3, 2, 5], f"do not sort or remove repeated channels: got {got}"


@pytest.mark.parametrize(
    "text",
    ["", "1,3", "(1,3)", "@1,3", "(@)", "(@ )", "(@1,)", "(@,1)",
     "(@1,,2)", "(@0)", "(@-1)", "(@+1)", "(@1.0)", "(@one)",
     "(@4:1)", "(@0:2)", "(@1:0)", "(@1:)", "(@:2)", "(@1:2:3)",
     "(@1 2)", "(@1;2)", "(@1))", "prefix(@1)", "(@1)tail", "( @1)",
     "(@\u0661)", "(@1-3)"],
)
def test_e4_rejects_malformed_channel_lists(text: str) -> None:
    with pytest.raises(ValueError):
        split_channels(text)
