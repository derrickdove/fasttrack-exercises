"""Checks for station fixture behavior, including real pytest teardown."""
from collections.abc import Callable
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from starter.fakes import FakeInstrument
from starter.fixtures_learner import Reading, powered_psu as powered_psu_fixture


@pytest.fixture(scope="module")
def issued_psus() -> list[FakeInstrument]:
    """Retain identities so E1 can detect reuse across test functions."""
    return []


def test_e1_identification_is_fresh(
    fake_psu: FakeInstrument, issued_psus: list[FakeInstrument]
) -> None:
    assert isinstance(fake_psu, FakeInstrument), "Return the supplied FakeInstrument"
    assert fake_psu not in issued_psus, "Each test must receive a new fake_psu"
    issued_psus.append(fake_psu)
    assert fake_psu.writes == [], "A fresh power supply has no write history"
    assert fake_psu.query("*IDN?") == "ACME,PSU-28,SIM001,1.0", "Use the specified ID reply"
    fake_psu.write("SYST:REM")
    assert fake_psu.writes == ["SYST:REM"], "The fake must record commands"


def test_e1_voltage_is_fresh(
    fake_psu: FakeInstrument, issued_psus: list[FakeInstrument]
) -> None:
    assert fake_psu not in issued_psus, "fake_psu must be function-scoped, not shared"
    issued_psus.append(fake_psu)
    assert fake_psu.writes == [], "Previous tests must not leave commands in this fake"
    for _ in range(2):
        assert fake_psu.query("MEAS:VOLT?") == "28.0", "Voltage replies are repeatable strings"
    assert fake_psu.writes == [], "Queries do not count as writes"
    with pytest.raises(KeyError):
        fake_psu.query("UNSCRIPTED?")
    fake_psu.write("SYST:LOCAL")


def test_e2_limits_path(limits_file: Path, tmp_path: Path) -> None:
    assert isinstance(limits_file, Path), "Return a pathlib.Path, not a string or open file"
    assert limits_file == tmp_path / "limits.csv", "Create limits.csv directly inside tmp_path"
    assert limits_file.is_file(), "Write the file before returning its path"


def test_e2_limits_contents(limits_file: Path) -> None:
    with limits_file.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["name", "low", "high", "unit"], "Use the specified CSV header"
        rows = list(reader)
    expected = [
        {"name": "bus_voltage", "low": "27.0", "high": "29.0", "unit": "V"},
        {"name": "supply_current", "low": "0.0", "high": "2.0", "unit": "A"},
    ]
    assert rows == expected, f"Expected the two station limit rows, got {rows!r}"


def test_e3_output_is_enabled(
    powered_psu: FakeInstrument, fake_psu: FakeInstrument
) -> None:
    assert powered_psu is fake_psu, "Yield the dependency, rather than creating another supply"
    assert fake_psu.writes == ["OUTP ON"], "Enable output before yielding; disable it after the test"
    assert powered_psu.query("MEAS:VOLT?") == "28.0", "The powered supply keeps its scripted replies"


@pytest.mark.parametrize("fails", [False, True], ids=["passing-test", "failing-test"])
def test_e3_cleanup_after_test_outcome(
    powered_psu: FakeInstrument, tmp_path: Path, fails: bool
) -> None:
    # Request the learner fixture here too: unfinished starters fail with NotImplementedError.
    assert isinstance(powered_psu, FakeInstrument), "Yield the power supply to the test"
    probe = tmp_path / "test_probe.py"
    probe.write_text(
        textwrap.dedent(
            f"""
            import json
            from pathlib import Path
            import pytest
            from starter.fixtures_learner import fake_psu, powered_psu

            @pytest.fixture
            def observe_cleanup(fake_psu):
                yield
                Path("writes.json").write_text(json.dumps(fake_psu.writes), encoding="utf-8")

            def test_e3_station_probe(observe_cleanup, powered_psu, fake_psu):
                assert powered_psu is fake_psu
                assert powered_psu.writes == ["OUTP ON"]
                powered_psu.write("MEAS:START")
                assert {not fails!r}, "Deliberate station test failure"
            """
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update(
        PYTHONPATH=str(Path(__file__).resolve().parents[1]),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTEST_ADDOPTS="",
        PYTHONDONTWRITEBYTECODE="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(probe), "-q", "--rootdir", str(tmp_path),
         "-o", "addopts=", "-p", "no:cacheprovider"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == (1 if fails else 0), (
        f"Probe should {'fail deliberately' if fails else 'pass'}:\n{result.stdout}\n{result.stderr}"
    )
    log = tmp_path / "writes.json"
    assert log.is_file(), "The teardown observer must run after the station test"
    writes = json.loads(log.read_text(encoding="utf-8"))
    assert writes == ["OUTP ON", "MEAS:START", "OUTP OFF"], (
        f"Teardown must disable output even after a failed assertion; got {writes!r}"
    )


def test_e3_cleanup_after_enable_error(powered_psu: FakeInstrument) -> None:
    # Request the fixture so unfinished starters fail with NotImplementedError.
    assert isinstance(powered_psu, FakeInstrument), "Yield the power supply to the test"
    enable_error = RuntimeError("Output enable failed after recording the command")

    class EnableErrorInstrument(FakeInstrument):
        def write(self, command: str) -> None:
            super().write(command)
            if command == "OUTP ON":
                raise enable_error

    probe = EnableErrorInstrument({})
    # Drive setup directly to check the identity of the propagated exception.
    setup = powered_psu_fixture.__wrapped__(probe)
    with pytest.raises(RuntimeError) as caught:
        next(setup)
    assert caught.value is enable_error, "Propagate the original enable error unchanged"
    assert probe.writes == ["OUTP ON", "OUTP OFF"], (
        f"Attempt OFF even when enabling output raises; got {probe.writes!r}"
    )


def test_e4_reading_defaults(make_reading: Callable[..., Reading]) -> None:
    assert callable(make_reading), "Return a factory function, not a Reading dictionary"
    assert make_reading() == {"name": "bus_voltage", "value": 28.0, "unit": "V"}, (
        "Use all three specified defaults"
    )


@pytest.mark.parametrize(
    "name,value,unit",
    [("supply_current", 1.2, "A"), ("offset", -0.5, "V"), ("", 0.0, "")],
)
def test_e4_reading_overrides(
    make_reading: Callable[..., Reading], name: str, value: float, unit: str
) -> None:
    expected = {"name": name, "value": value, "unit": unit}
    assert make_reading(name, value, unit) == expected, "Accept positional overrides unchanged"
    assert make_reading(name=name, value=value, unit=unit) == expected, "Accept keyword overrides unchanged"
    assert make_reading(value=value) == {"name": "bus_voltage", "value": value, "unit": "V"}, (
        "Omitted arguments keep their defaults, including when value is zero"
    )


def test_e4_readings_are_independent(make_reading: Callable[..., Reading]) -> None:
    first = make_reading()
    second = make_reading()
    assert first is not second, "Allocate a new Reading dictionary on each call"
    first["value"] = 99.0
    first["name"] = "changed"
    assert second == {"name": "bus_voltage", "value": 28.0, "unit": "V"}, "Readings must not share state"
    assert make_reading() == second, "Mutation must not change future defaults"
