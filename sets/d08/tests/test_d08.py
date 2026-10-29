from pathlib import Path
import subprocess
import sys
from typing import get_type_hints

import pytest

import starter.units as units
from starter.units.convert import to_base
from starter.units.parse import parse_quantity


@pytest.mark.parametrize(
    "value, unit, expected_value, expected_unit",
    [
        (250.0, "mV", 0.25, "V"),
        (1.2, "kV", 1200.0, "V"),
        (20.0, "mA", 0.02, "A"),
        (75.0, "uA", 0.000075, "A"),
        (4.7, "kOhm", 4700.0, "Ohm"),
        (2.2, "MOhm", 2200000.0, "Ohm"),
    ],
)
def test_e1_prefixed_station_readings(
    value: float, unit: str, expected_value: float, expected_unit: str
) -> None:
    got = to_base(value, unit)
    assert isinstance(got, tuple) and len(got) == 2, "Return (value, unit) as a tuple"
    assert isinstance(got[0], float), "The converted value must be a float"
    assert got[0] == pytest.approx(expected_value), f"Wrong scaling for {value} {unit}"
    assert got[1] == expected_unit, f"Wrong base unit for {unit}"


@pytest.mark.parametrize("value", [0.0, -3.3, 0.125])
def test_e1_preserves_sign_and_zero(value: float) -> None:
    got = to_base(value, "mV")
    assert got == (pytest.approx(value / 1000), "V"), f"Check sign/zero for {value} mV"


@pytest.mark.parametrize("unit", ["", "MV", "mv", " KOhm", "mV ", "V", "A", "Ohm", "Hz"])
def test_e1_rejects_unknown_units(unit: str) -> None:
    with pytest.raises(ValueError):
        to_base(1.0, unit)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("4.7 kOhm", (4.7, "kOhm")),
        ("250mV", (250.0, "mV")),
        ("-3.3 V", (-3.3, "V")),
        ("2 kV", (2.0, "kV")),
        ("8mA", (8.0, "mA")),
        ("75 uA", (75.0, "uA")),
        ("2.2 MOhm", (2.2, "MOhm")),
        ("1 A", (1.0, "A")),
        ("100 Ohm", (100.0, "Ohm")),
    ],
)
def test_e2_reads_station_quantity_without_scaling(text: str, expected: tuple[float, str]) -> None:
    got = parse_quantity(text)
    assert isinstance(got, tuple) and len(got) == 2, "Return (value, unit) as a tuple"
    assert isinstance(got[0], float), "Parse the reading as a float"
    assert got == expected, f"For {text!r}, expected {expected!r}; do not scale the value"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("  +.5mV  ", (0.5, "mV")),
        ("\t-0.25\tA\n", (-0.25, "A")),
        ("2. V", (2.0, "V")),
        ("0003Ohm", (3.0, "Ohm")),
        ("0mA", (0.0, "mA")),
    ],
)
def test_e2_decimal_forms_and_whitespace(text: str, expected: tuple[float, str]) -> None:
    assert parse_quantity(text) == expected, f"Check decimal/whitespace handling for {text!r}"


@pytest.mark.parametrize(
    "text",
    ["", "   ", "4.7", "mV", "4.7 Hz", "250mv", "4,7 kOhm", "1e3 V",
     "NaN V", "inf A", "--3 V", "3.2.1 V", "3 V extra", "3 m V", "1 2 V"],
)
def test_e2_rejects_malformed_station_input(text: str) -> None:
    with pytest.raises(ValueError):
        parse_quantity(text)


def test_e3_reexports_original_functions() -> None:
    assert units.to_base is to_base, "Re-export to_base from .convert without wrapping it"
    assert units.parse_quantity is parse_quantity, "Re-export parse_quantity from .parse"


def test_e3_declares_public_names() -> None:
    names = units.__all__
    assert isinstance(names, list), "__all__ must be a list of public name strings"
    assert len(names) == 2 and set(names) == {"to_base", "parse_quantity"}, (
        "__all__ must contain exactly to_base and parse_quantity (either order)"
    )
    for name in names:
        assert callable(getattr(units, name)), f"Public name {name!r} must be callable"


def test_e4_package_passes_strict_mypy(tmp_path: Path) -> None:
    # A raising stub type-checks; call the APIs first so E4 starts unfinished too.
    to_base(250.0, "mV")
    parse_quantity("250mV")
    set_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "--cache-dir", str(tmp_path / "mypy-cache"),
         str(set_root / "starter" / "units")],
        cwd=set_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=8,
    )
    assert result.returncode == 0, "Fix the mypy errors below:\n" + result.stdout + result.stderr


def test_e4_keeps_driver_api_annotations() -> None:
    to_base(250.0, "mV")
    parse_quantity("250mV")
    expected_convert = {"value": float, "unit": str, "return": tuple[float, str]}
    expected_parse = {"text": str, "return": tuple[float, str]}
    assert get_type_hints(to_base) == expected_convert, "Keep E1's supplied type hints"
    assert get_type_hints(parse_quantity) == expected_parse, "Keep E2's supplied type hints"
