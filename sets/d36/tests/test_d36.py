"""Offline station deployment checks: no Linux service is installed or started."""
from configparser import ConfigParser
from copy import deepcopy
from pathlib import Path
import tomllib

import pytest

from starter.units import load_station_toml, parse_unit, validate_unit


@pytest.fixture
def service_file() -> ConfigParser:
    path = Path(__file__).resolve().parents[1] / "starter" / "chassis-demo.service"
    text = path.read_text(encoding="utf-8")
    if "# NotImplementedError: E1:" in text:
        raise NotImplementedError("E1: Replace the service file placeholder using README.md")
    parser = ConfigParser(strict=False, interpolation=None, delimiters=("=",))
    parser.optionxform = str
    parser.read_string(text)
    return parser


def test_e1_network_ordering(service_file: ConfigParser) -> None:
    assert service_file.has_section("Unit"), "Add a [Unit] section"
    unit = service_file["Unit"]
    assert unit.get("Description", "").strip(), "Describe the station service"
    for key in ("After", "Wants"):
        assert "network-online.target" in unit.get(key, "").split(), f"{key} must name network-online.target"


def test_e1_service_policy(service_file: ConfigParser) -> None:
    assert service_file.has_section("Service"), "Add a [Service] section"
    service = service_file["Service"]
    assert service.get("Type") == "simple", "Use Type=simple for the station process"
    command = service.get("ExecStart", "").split()
    assert len(command) >= 3, "ExecStart needs the Python path, -m, and chassis"
    assert command[0].startswith("/"), "Use an absolute Linux Python path"
    assert command[0].rsplit("/", 1)[-1] in ("python", "python3"), "Use python or python3"
    assert command[1:3] == ["-m", "chassis"], "Start the chassis module"
    assert service.get("Restart") == "on-failure", "Restart the station after a failure"
    assert int(service.get("RestartSec", "0")) > 0, "RestartSec must be positive whole seconds"
    assert service.get("User", "").strip() not in ("", "root", "0"), "Choose a named non-root service user"


def test_e1_boot_target(service_file: ConfigParser) -> None:
    assert service_file.has_section("Install"), "Add an [Install] section"
    assert "multi-user.target" in service_file["Install"].get("WantedBy", "").split(), "Use the normal multi-user boot target"


def test_e2_sections_and_whitespace(tmp_path: Path) -> None:
    path = tmp_path / "station.service"
    path.write_text("  # station comment\n; another comment\n\n[ Unit ]\n Description = Rack 7 \n[Service]\nType=simple\n", encoding="utf-8")
    expected = {"Unit": {"Description": ["Rack 7"]}, "Service": {"Type": ["simple"]}}
    assert parse_unit(str(path)) == expected, "Strip surrounding whitespace and skip whole-line comments"


def test_e2_repeats_empty_values_and_literal_text(tmp_path: Path) -> None:
    path = tmp_path / "repeat.service"
    path.write_text("[Service]\nEnvironment=MODE=demo\nEnvironment=\nEnvironment=LOAD=100% # literal; text\nUser=chassis\nuser=other\n[Service]\nEnvironment=NEXT=2\n", encoding="utf-8")
    expected = {"Service": {"Environment": ["MODE=demo", "", "LOAD=100% # literal; text", "NEXT=2"], "User": ["chassis"], "user": ["other"]}}
    assert parse_unit(path) == expected, "Keep every assignment, case, empty value, and text after the first ="


@pytest.mark.parametrize("character", ["\v", "\f", "\x1c", "\x1d", "\x1e", "\u0085", "\u2028", "\u2029"])
def test_e2_preserves_literal_characters_inside_values(tmp_path: Path, character: str) -> None:
    path = tmp_path / "literal.service"
    value = f"LABEL=alpha{character}beta"
    path.write_text(f"[Service]\nEnvironment={value}\n", encoding="utf-8")
    assert parse_unit(path) == {"Service": {"Environment": [value]}}, "Keep all characters inside values"


def test_e2_empty_file_and_empty_sections(tmp_path: Path) -> None:
    path = tmp_path / "empty.service"
    path.write_text("# no settings\n", encoding="utf-8")
    assert parse_unit(path) == {}, "A comment-only file has no sections"
    path.write_text("[Unit]\n[Service]\n", encoding="utf-8")
    assert parse_unit(path) == {"Unit": {}, "Service": {}}, "Keep empty sections"


@pytest.mark.parametrize("text, line", [
    ("# heading\nUser=chassis\n", 2),
    ("[Service]\nRestart on-failure\n", 2),
    ("[Service]\n = value\n", 2),
    ("[ ]\n", 1),
    ("[Service\n", 1),
])
def test_e2_bad_lines_name_line_number(tmp_path: Path, text: str, line: int) -> None:
    path = tmp_path / "broken.service"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=rf"line {line}\b"):
        parse_unit(path)


def test_e2_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_unit(tmp_path / "absent.service")


@pytest.fixture
def valid_unit() -> dict[str, dict[str, list[str]]]:
    return {
        "Unit": {"Description": ["Rack 7"], "After": ["network-online.target"], "Wants": ["network-online.target"]},
        "Service": {"Type": ["simple"], "ExecStart": ["/opt/station/python -m chassis --help"], "Restart": ["on-failure"], "RestartSec": ["3"], "User": ["chassis"]},
        "Install": {"WantedBy": ["multi-user.target"]},
    }


def test_e3_valid_unit_and_no_mutation(valid_unit: dict[str, dict[str, list[str]]]) -> None:
    before = deepcopy(valid_unit)
    assert validate_unit(valid_unit) == [], "A valid station unit has no problems"
    assert valid_unit == before, "Checking a unit must not change it"


def test_e3_empty_unit_reports_checklist_in_order() -> None:
    expected = [
        "Description missing",
        "After must include network-online.target",
        "Wants must include network-online.target",
        "Type must be simple",
        "ExecStart must run an absolute python -m chassis command",
        "Restart missing",
        "RestartSec missing",
        "User missing",
        "WantedBy must include multi-user.target",
    ]
    assert validate_unit({}) == expected, "Report every missing setting in checklist order"


@pytest.mark.parametrize("section, key, message", [
    ("Unit", "Description", "Description missing"),
    ("Unit", "After", "After must include network-online.target"),
    ("Unit", "Wants", "Wants must include network-online.target"),
    ("Service", "Type", "Type must be simple"),
    ("Service", "ExecStart", "ExecStart must run an absolute python -m chassis command"),
    ("Service", "Restart", "Restart missing"),
    ("Service", "RestartSec", "RestartSec missing"),
    ("Service", "User", "User missing"),
    ("Install", "WantedBy", "WantedBy must include multi-user.target"),
])
@pytest.mark.parametrize("values", [None, [], ["  "]])
def test_e3_missing_and_blank_settings(valid_unit: dict[str, dict[str, list[str]]], section: str, key: str, message: str, values: list[str] | None) -> None:
    if values is None:
        del valid_unit[section][key]
    else:
        valid_unit[section][key] = values
    assert validate_unit(valid_unit) == [message], f"Name the missing {section}.{key} setting"


@pytest.mark.parametrize("section, key, value, message", [
    ("Service", "User", "root", "User is root"),
    ("Service", "User", "0", "User is root"),
    ("Service", "Type", "forking", "Type must be simple"),
    ("Service", "Restart", "always", "Restart must be on-failure"),
    ("Service", "RestartSec", "0", "RestartSec must be positive whole seconds"),
    ("Service", "RestartSec", "-2", "RestartSec must be positive whole seconds"),
    ("Service", "RestartSec", "0.5", "RestartSec must be positive whole seconds"),
    ("Service", "RestartSec", "3s", "RestartSec must be positive whole seconds"),
    ("Service", "ExecStart", "python -m chassis", "ExecStart must run an absolute python -m chassis command"),
    ("Service", "ExecStart", "/usr/bin/python -m unrelated", "ExecStart must run an absolute python -m chassis command"),
    ("Service", "ExecStart", "/usr/bin/echo python -m chassis", "ExecStart must run an absolute python -m chassis command"),
    ("Unit", "After", "not-network-online.target", "After must include network-online.target"),
    ("Install", "WantedBy", "graphical.target", "WantedBy must include multi-user.target"),
])
def test_e3_invalid_values(valid_unit: dict[str, dict[str, list[str]]], section: str, key: str, value: str, message: str) -> None:
    valid_unit[section][key] = [value]
    assert validate_unit(valid_unit) == [message], f"Reject {section}.{key}={value!r}"


def test_e3_repeated_settings(valid_unit: dict[str, dict[str, list[str]]]) -> None:
    valid_unit["Unit"]["After"] = ["network-online.target", "time-sync.target"]
    valid_unit["Unit"]["Wants"] = ["time-sync.target", "network-online.target"]
    valid_unit["Install"]["WantedBy"] = ["multi-user.target", "graphical.target"]
    valid_unit["Service"]["User"] = ["root", " chassis "]
    valid_unit["Service"]["Restart"] = ["always", " on-failure "]
    valid_unit["Service"]["ExecStart"] = ["/usr/bin/python3 -m chassis"]
    valid_unit["Other"] = {"Extra": ["ignored"]}
    assert validate_unit(valid_unit) == [], "Combine dependency lists; use the last scalar value; ignore extra settings"
    valid_unit["Service"]["User"].append("root")
    assert validate_unit(valid_unit) == ["User is root"], "The final User assignment controls this checklist"


@pytest.fixture
def station_text() -> str:
    return '''[station]
name = "Rack 7"
operator_note = "Keep this extra key"

[[instruments]]
id = "psu1"
kind = "psu"
resource = "TCPIP::10.0.0.5::5025::SOCKET"

[[instruments]]
id = "dmm1"
kind = "dmm"
resource = "TCPIP::10.0.0.6::5025::SOCKET"
'''


def test_e4_loads_complete_dict(tmp_path: Path, station_text: str) -> None:
    path = tmp_path / "station.toml"
    path.write_text(station_text, encoding="utf-8")
    assert load_station_toml(str(path)) == tomllib.loads(station_text), "Return all loaded data, including extra keys"


@pytest.mark.parametrize("text, key_path", [
    ('instruments = []\n', "station"),
    ('station = "Rack 7"\ninstruments = []\n', "station"),
    ('[station]\n', "station.name"),
    ('[station]\nname = true\n', "station.name"),
    ('[station]\nname = 7\n', "station.name"),
    ('[station]\nname = "A"\n', "instruments"),
    ('instruments = "psu1"\n[station]\nname = "A"\n', "instruments"),
    ('instruments = {}\n[station]\nname = "A"\n', "instruments"),
    ('instruments = [7]\n[station]\nname = "A"\n', "instruments[0]"),
])
def test_e4_container_and_station_errors(tmp_path: Path, text: str, key_path: str) -> None:
    path = tmp_path / "station.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError) as caught:
        load_station_toml(path)
    assert key_path in str(caught.value), f"Name the failing key path {key_path!r}"


@pytest.mark.parametrize("key", ["id", "kind", "resource"])
@pytest.mark.parametrize("replacement", [None, "42", "false", "[]", "{}"])
def test_e4_instrument_field_errors(tmp_path: Path, station_text: str, key: str, replacement: str | None) -> None:
    # Damage only the second instrument, so its index must be reported.
    first, second = station_text.rsplit("[[instruments]]", 1)
    lines = second.splitlines()
    lines = [line if not line.startswith(key + " =") else (f"{key} = {replacement}" if replacement is not None else "") for line in lines]
    path = tmp_path / "station.toml"
    path.write_text(first + "[[instruments]]" + "\n".join(lines), encoding="utf-8")
    with pytest.raises(ValueError) as caught:
        load_station_toml(path)
    expected = f"instruments[1].{key}"
    assert expected in str(caught.value), f"Report the exact instrument field {expected}"


def test_e4_empty_list_and_strings_are_valid(tmp_path: Path) -> None:
    path = tmp_path / "station.toml"
    path.write_text('instruments = []\n[station]\nname = ""\n', encoding="utf-8")
    assert load_station_toml(path) == {"station": {"name": ""}, "instruments": []}, "This loader checks types, allowing empty strings and an empty instrument list"
    path.write_text('[station]\nname = "A"\n[[instruments]]\nid = ""\nkind = "simulator"\nresource = ""\n', encoding="utf-8")
    assert load_station_toml(path)["instruments"][0]["kind"] == "simulator", "Kind is a string here; deployment policy is outside this exercise"


def test_e4_bad_toml(tmp_path: Path) -> None:
    path = tmp_path / "broken.toml"
    path.write_text("[station\nname = ?", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        load_station_toml(path)


def test_e4_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_station_toml(tmp_path / "absent.toml")
