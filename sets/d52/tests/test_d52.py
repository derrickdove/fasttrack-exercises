"""Public contracts for the unfamiliar-codebase exercises."""

import hashlib
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from starter.map_answers import map_answers
from starter.legacy_station.base import Driver
from starter.legacy_station.limits import check_limits
from starter.legacy_station.load import ElectronicLoad
from starter.legacy_station.runner import Step, run_station
from starter.legacy_station.tests.fakes import FakeTransport

SET = Path(__file__).resolve().parents[1]
REGRESSION = Path("starter/legacy_station/tests/test_regression.py")
ORIGINAL_LIMITS = '"""Numerical acceptance checks shared by all station instruments.\n\nA limits band has a lower and upper bound in the measurement\'s own unit.\nInvalid configuration or a nonfinite measurement is an error, not a pass.\nKeep that distinction: the runner records errors separately from failures.\n"""\n\nimport math\n\n\ndef validate_limits(low: float, high: float) -> None:\n    """Reject reversed bounds, infinity, or NaN before a step starts."""\n    if not math.isfinite(low) or not math.isfinite(high) or low > high:\n        raise ValueError("limits must be finite and ordered")\n\n\ndef check_limits(value: float, low: float, high: float) -> bool:\n    """Compare a finite measurement with the configured acceptance band.\n\n    Units are already consistent at the call site. No rounding, conversion,\n    or instrument communication belongs in this shared numeric helper.\n    """\n    validate_limits(low, high)\n    if not math.isfinite(value):\n        raise ValueError("measurement must be finite")\n    return low < value < high\n'


def check_answer(question: str, digest: str, hint: str) -> None:
    answers = map_answers()
    assert isinstance(answers, dict), "Return a dictionary of question IDs and option letters"
    assert set(answers) == {"Q1", "Q2", "Q3"}, "Return exactly Q1, Q2, and Q3"
    choice = answers[question]
    assert isinstance(choice, str), "Each answer must be an uppercase option letter"
    if hashlib.sha256(choice.encode("utf-8")).hexdigest() != digest:
        pytest.fail(f"{question}: reread {hint}", pytrace=False)


def test_e1_query_timeout_path() -> None:
    check_answer("Q1", "df7e70e5021544f4834bbee64a9e3789febc4be81470df629cad6ddb03320a5c", "the query call path, from a driver's read() to its transport")


def test_e1_acceptance_owner() -> None:
    check_answer("Q2", "6b23c0d5f35d1b11f9b683f0b0a617355deb11277d91ae091d399c655b87940d", "the numerical decision called by the runner")


def test_e1_new_driver_interface() -> None:
    check_answer("Q3", "559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd", "the existing instrument class declarations")


def require_regression() -> Path:
    path = SET / REGRESSION
    if not path.is_file():
        raise NotImplementedError("E3: add starter/legacy_station/tests/test_regression.py")
    return path


def run_package(tmp_path: Path, name: str, target: str, *, original: bool = False) -> tuple[subprocess.CompletedProcess[str], ET.Element]:
    sandbox = tmp_path / name
    shutil.copytree(SET / "starter", sandbox / "starter",
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".mypy_cache"))
    if original:
        (sandbox / "starter/legacy_station/limits.py").write_text(ORIGINAL_LIMITS, encoding="utf-8")
    report = sandbox / "report.xml"
    env = os.environ.copy()
    env.update(PYTHONPATH=str(sandbox), PYTEST_ADDOPTS="", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTEST_PLUGINS", None)
    command = [sys.executable, "-m", "pytest", target, "-q", "-p", "no:cacheprovider",
               "-o", "addopts=", "--confcutdir", str(sandbox), "--junitxml", str(report)]
    completed = subprocess.run(command, cwd=sandbox, env=env, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=20)
    assert report.is_file(), "Package tests must produce a report:\n" + completed.stdout + completed.stderr
    return completed, ET.parse(report).getroot()


@pytest.mark.parametrize("current,reply,timeout", [
    (0.0, " 0.000\n", 0.4), (10.0, "9.875", 1.25),
    (1.2346, " 1.234567 ", 0.05), (0.5, "-0.002", 0.4),
])
def test_e2_load_commands_and_runner(current: float, reply: str, timeout: float) -> None:
    transport = FakeTransport({"MEAS:CURR?": reply, "*IDN?": "LOAD,L1\n"})
    load = ElectronicLoad(transport, timeout_s=timeout)
    load.set_current(current)
    assert isinstance(load, Driver), "follow the station's driver base-class pattern"
    load.enable(True)
    load.enable(False)
    assert transport.writes == [(f"CURR {current:.3f}", timeout), ("INPUT ON", timeout), ("INPUT OFF", timeout)], (
        "send exactly one correctly formatted command per request, with the configured timeout"
    )
    assert load.read() == float(reply), "return current without clipping or rounding"
    assert load.identify() == "LOAD,L1", "keep the inherited identification behavior"
    assert transport.queries == [("MEAS:CURR?", timeout), ("*IDN?", timeout)]
    drivers: dict[str, Driver] = {"load": load}
    value = float(reply)
    rows = run_station(drivers, [Step("draw", "load", value - 1, value + 1)])
    assert (rows[0].value, rows[0].status) == (value, "PASS"), "the generic runner must accept the third driver"


@pytest.mark.parametrize("current,reply", [
    (-0.001, "bad"), (10.001, "nan"), (float("nan"), "inf"),
    (float("inf"), "-inf"), (-float("inf"), "1 A"), (-1.0, ""),
])
def test_e2_load_rejects_bad_inputs(current: float, reply: str) -> None:
    transport = FakeTransport({"MEAS:CURR?": reply})
    load = ElectronicLoad(transport)
    with pytest.raises(ValueError):
        load.set_current(current)
    assert transport.writes == [], "reject invalid current before writing"
    assert transport.queries == [], "setting current must not query the instrument"
    with pytest.raises(ValueError):
        load.read()
    assert transport.queries == [("MEAS:CURR?", 0.4)], "a malformed reply is not retried"


def test_e2_load_errors_and_old_suite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    transport = FakeTransport({"MEAS:CURR?": "1"})
    load = ElectronicLoad(transport)
    assert load.read() == 1.0  # The E2 stub must fail directly before the subprocess check.
    for operation in ["read", "set_current", "enable"]:
        failure = TimeoutError("instrument silent")
        calls: list[tuple[str, float]] = []

        def broken(command: str, timeout_s: float) -> str:
            calls.append((command, timeout_s))
            raise failure

        with monkeypatch.context() as patch:
            patch.setattr(transport, "query" if operation == "read" else "write", broken)
            with pytest.raises(TimeoutError) as caught:
                if operation == "read":
                    load.read()
                elif operation == "set_current":
                    load.set_current(1.0)
                else:
                    load.enable(True)
        assert caught.value is failure, "let the original transport exception reach the caller"
        assert len(calls) == 1, "do not retry commands or queries"
    for timeout in [0.0, -1.0, float("nan"), float("inf")]:
        with pytest.raises(ValueError):
            ElectronicLoad(transport, timeout_s=timeout)
    completed, report = run_package(tmp_path, "old_suite", "starter/legacy_station/tests/test_existing.py")
    assert completed.returncode == 0, "Keep the existing package tests passing:\n" + completed.stdout + completed.stderr
    assert len(report.findall(".//testcase")) >= 6, "the existing tests must actually run"


@pytest.mark.parametrize("low,high", [(4.75, 5.25), (-3.0, -1.0), (0.0, 0.0)])
def test_e3_closed_band_and_validation(low: float, high: float) -> None:
    require_regression()
    assert check_limits(low, low, high), "the lower configured endpoint must pass"
    assert check_limits(high, low, high), "the upper configured endpoint must pass"
    assert not check_limits(math.nextafter(low, -math.inf), low, high), "do not widen the band below low"
    assert not check_limits(math.nextafter(high, math.inf), low, high), "do not widen the band above high"
    for value in [float("nan"), float("inf"), -float("inf")]:
        with pytest.raises(ValueError):
            check_limits(value, low, high)
        with pytest.raises(ValueError):
            check_limits(low, value, high)
        with pytest.raises(ValueError):
            check_limits(high, low, value)
    with pytest.raises(ValueError):
        check_limits(0, 2, 1)


def test_e3_regression_passes_repair_and_rejects_original(tmp_path: Path) -> None:
    require_regression()
    completed, healthy = run_package(tmp_path, "repaired", "starter/legacy_station/tests")
    assert completed.returncode == 0, "The old tests and your new regression must pass together:\n" + completed.stdout + completed.stderr
    regressions = [case for case in healthy.findall(".//testcase")
                   if "test_regression" in case.get("classname", "")]
    assert regressions and all(case.get("name", "").startswith("test_e3_") for case in regressions), (
        "add at least one collected test_e3_* function in test_regression.py"
    )
    assert not healthy.findall(".//skipped"), "the regression must run rather than skip"
    completed, mutant = run_package(tmp_path, "original", REGRESSION.as_posix(), original=True)
    assert completed.returncode == 1, "Your regression must reject the original defect:\n" + completed.stdout + completed.stderr
    assert len(mutant.findall(".//testcase")) == len(regressions), "run the same regression cases against both versions"
    assert not mutant.findall(".//error"), "an import or fixture error is not evidence of catching the defect"
    failures = mutant.findall(".//failure")
    assert failures and all("AssertionError" in failure.get("message", "") for failure in failures), (
        "catch the original defect with a failing assertion, not an unrelated exception"
    )
