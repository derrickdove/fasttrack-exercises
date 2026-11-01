"""Offline station deployment checks: no Linux service is installed or started."""
from configparser import ConfigParser
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tomllib

import pytest

from starter.units import diagnose_service, load_station_toml, parse_unit, validate_unit


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
    assert service.get("Type") == "oneshot", "Use Type=oneshot for the saved-file check"
    command = service.get("ExecStart", "").split()
    assert len(command) >= 4, "ExecStart needs the Python path, -m, chassis, and check"
    assert command[0].startswith("/"), "Use an absolute Linux Python path"
    assert command[0].rsplit("/", 1)[-1] in ("python", "python3"), "Use python or python3"
    assert command[1:4] == ["-m", "chassis", "check"], "Run the one-shot chassis check"
    assert service.get("Restart") == "no", "A FAIL result must not automatically re-run the check"
    assert service.get("User", "").strip() not in ("", "root", "0"), "Choose a named non-root service user"


def test_e1_boot_target(service_file: ConfigParser) -> None:
    assert service_file.has_section("Install"), "Add an [Install] section"
    assert "multi-user.target" in service_file["Install"].get("WantedBy", "").split(), "Use the normal multi-user boot target"


@pytest.mark.parametrize("key, value, problem", [
    ("Type", "simple", "Type must be oneshot"),
    ("Restart", "on-failure", "Restart must be no"),
    ("Restart", "", "Restart missing"),
    ("ExecStart", "/opt/chassis/bin/python -m chassis worker",
     "ExecStart must run an absolute python -m chassis check command"),
    ("User", "root", "User is root"),
    ("User", "0", "User is root"),
])
def test_e1_supplied_validator_policy(service_file: ConfigParser, key: str, value: str, problem: str) -> None:
    path = Path(__file__).resolve().parents[1] / "starter" / "chassis-demo.service"
    parsed = parse_unit(path)
    parsed["Service"].pop("RestartSec", None)
    assert validate_unit(parsed) == [], "The one-shot unit needs no restart delay"
    changed = deepcopy(parsed)
    changed["Service"][key] = [value]
    assert validate_unit(changed) == [problem], f"Reject unsafe one-shot policy: {key}={value}"


def _check_answer_shape(answers: dict[str, dict[str, str]]) -> None:
    __tracebackhide__ = True
    if not isinstance(answers, dict) or set(answers) != {"case_01", "case_02", "case_03", "case_04"}:
        pytest.fail("E2: Return exactly the four case IDs documented in README.md.", pytrace=False)
    for case_id, answer in answers.items():
        if (not isinstance(answer, dict) or set(answer) != {"cause", "fix"}
                or not all(isinstance(value, str) for value in answer.values())):
            pytest.fail(f"E2: {case_id} needs exactly two string fields: cause and fix.", pytrace=False)


def _check_recorded_answer(answers: dict[str, dict[str, str]], case_id: str) -> None:
    __tracebackhide__ = True
    _check_answer_shape(answers)
    # Store SHA-256 digests (fixed-length fingerprints), not readable diagnoses.
    answer_digests = {
        "case_01": "b9b48e8d189efc9ff38f78d63164dd8e64d13cfdb57013a931c926a442ce1cfd",
        "case_02": "11a02b62b8664cf1c3ef4d060bd4c1c338f8b64784c505059173477f1b93ce10",
        "case_03": "ea4f13280587d937fbf6e1bbf8c17f0378c222f1e7b033268fe2ba8afc7e4a0f",
        "case_04": "a14b9375619a92775a68a4e9b48b5e1980b23e67616d8c987f7f571647294b44",
    }
    actual = hashlib.sha256(json.dumps(answers[case_id], sort_keys=True).encode("utf-8")).hexdigest()
    if actual != answer_digests[case_id]:
        pytest.fail(f"E2: Revisit both recordings for {case_id}; review the cause and fix.", pytrace=False)


def test_e2_answer_sheet_shape() -> None:
    _check_answer_shape(diagnose_service())


@pytest.mark.parametrize("case_id", ["case_01", "case_02", "case_03"])
def test_e2_recorded_failures(case_id: str) -> None:
    _check_recorded_answer(diagnose_service(), case_id)


def test_e2_additional_recording() -> None:
    _check_recorded_answer(diagnose_service(), "case_04")


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


def test_e3_loads_complete_dict(tmp_path: Path, station_text: str) -> None:
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
def test_e3_container_and_station_errors(tmp_path: Path, text: str, key_path: str) -> None:
    path = tmp_path / "station.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError) as caught:
        load_station_toml(path)
    assert key_path in str(caught.value), f"Name the failing key path {key_path!r}"


@pytest.mark.parametrize("key", ["id", "kind", "resource"])
@pytest.mark.parametrize("replacement", [None, "42", "false", "[]", "{}"])
def test_e3_instrument_field_errors(tmp_path: Path, station_text: str, key: str, replacement: str | None) -> None:
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


def test_e3_empty_list_and_strings_are_valid(tmp_path: Path) -> None:
    path = tmp_path / "station.toml"
    path.write_text('instruments = []\n[station]\nname = ""\n', encoding="utf-8")
    assert load_station_toml(path) == {"station": {"name": ""}, "instruments": []}, "This loader checks types, allowing empty strings and an empty instrument list"
    path.write_text('[station]\nname = "A"\n[[instruments]]\nid = ""\nkind = "simulator"\nresource = ""\n', encoding="utf-8")
    assert load_station_toml(path)["instruments"][0]["kind"] == "simulator", "Kind is a string here; deployment policy is outside this exercise"


def test_e3_bad_toml(tmp_path: Path) -> None:
    path = tmp_path / "broken.toml"
    path.write_text("[station\nname = ?", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        load_station_toml(path)


def test_e3_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_station_toml(tmp_path / "absent.toml")
