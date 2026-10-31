"""Grade learner-authored pytest tests against supplied and faulty station drivers."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from starter.test_scpi_learner import (
    test_e1_number_reply as number_test,
    test_e2_error_reply as error_test,
    test_e3_station_sweep as sweep_test,
    test_e4_overload_quirk as quirk_test,
)

SET = Path(__file__).resolve().parents[1]
NUMBERS = [
    ("0", 0.0), ("-12", -12.0), ("+3.5", 3.5),
    ("6.02E+2", 602.0), (" 7.25 ", 7.25), ("8.5\r\n", 8.5),
]
ERRORS = [
    ('0,"No error"', (0, "No error")),
    ('-100,"Command error"', (-100, "Command error")),
    (' -222, "Data out of range"\r\n', (-222, "Data out of range")),
    ('-300,"Relay, stuck"', (-300, "Relay, stuck")),
]

# Each replacement isolates one realistic driver mistake.
MUTANTS = {
    "number-sign": r"""
def parse_number(reply: str) -> float:
    return abs(float(reply.strip()))
""",
    "number-exponent": r"""
def parse_number(reply: str) -> float:
    return float(reply.strip().upper().split("E")[0])
""",
    "number-padding": r"""
def parse_number(reply: str) -> float:
    if reply != reply.strip():
        raise ValueError("unexpected padding")
    return float(reply)
""",
    "error-sign": r"""
_original_error = parse_error

def parse_error(reply: str) -> tuple[int, str]:
    code, message = _original_error(reply)
    return abs(code), message
""",
    "error-message": r"""
_original_error = parse_error

def parse_error(reply: str) -> tuple[int, str]:
    code, message = _original_error(reply)
    return code, message.upper()
""",
    "error-comma": r"""
_original_error = parse_error

def parse_error(reply: str) -> tuple[int, str]:
    code, message = _original_error(reply)
    return code, message.split(",")[0]
""",
    "sweep-channel": r"""
def build_query(channel: int) -> str:
    if channel <= 0:
        raise ValueError("channel must be positive")
    return "MEAS:VOLT? (@1)\n"
""",
    "sweep-validation": r"""
def build_query(channel: int) -> str:
    return f"MEAS:VOLT? (@{channel})\n"
""",
    "sweep-zero": r"""
_original_query = build_query

def build_query(channel: int) -> str:
    if channel == 0:
        return f"MEAS:VOLT? (@{channel})\n"
    return _original_query(channel)
""",
    "sweep-negative": r"""
_original_query = build_query

def build_query(channel: int) -> str:
    if channel < 0:
        return f"MEAS:VOLT? (@{channel})\n"
    return _original_query(channel)
""",
    "fixed-firmware": r"""
def read_voltage(reply: str) -> float:
    if reply == "OVLD":
        raise ValueError("overload")
    return parse_number(reply)
""",
}

# This subprocess-only reporter records pytest's own collection and outcomes.
REPORTER = r"""
import json
from pathlib import Path

state = {"items": [], "deselected": [], "results": [], "errors": []}


def pytest_collection_finish(session):
    for item in session.items:
        marks = [
            {"name": mark.name, "kwargs": mark.kwargs}
            for mark in item.iter_markers()
            if mark.name in ("slow", "xfail", "skip", "skipif")
        ]
        callspec = getattr(item, "callspec", None)
        state["items"].append({
            "name": getattr(item, "originalname", item.name),
            "nodeid": item.nodeid,
            "params": callspec.params if callspec is not None else None,
            "id": callspec.id if callspec is not None else None,
            "marks": marks,
        })


def pytest_deselected(items):
    state["deselected"].extend(getattr(item, "originalname", item.name) for item in items)


def pytest_collectreport(report):
    if report.failed:
        state["errors"].append(str(report.longrepr))


def pytest_runtest_logreport(report):
    if report.when == "call" or report.failed:
        state["results"].append({
            "nodeid": report.nodeid,
            "outcome": report.outcome,
            "xfail": getattr(report, "wasxfail", None),
            "detail": str(report.longrepr or ""),
        })


def pytest_sessionfinish(session):
    Path("events.json").write_text(json.dumps(state), encoding="utf-8")
"""

Run = Callable[..., dict[str, Any]]


@pytest.fixture(scope="module")
def run_driver() -> Iterator[Run]:
    temporary = tempfile.TemporaryDirectory(prefix="fasttrack-d12-")
    cache: dict[tuple[str, str, str], dict[str, Any]] = {}

    def run(variant: str = "good", target: str = "", marker: str = "") -> dict[str, Any]:
        key = variant, target, marker
        if key in cache:
            return cache[key]
        directory = Path(temporary.name) / f"driver-{len(cache)}"
        directory.mkdir()
        shutil.copyfile(SET / "starter" / "test_scpi_learner.py", directory / "test_scpi_learner.py")
        shutil.copyfile(SET / "pytest.ini", directory / "pytest.ini")
        driver = (SET / "scpi.py").read_text(encoding="utf-8")
        (directory / "scpi.py").write_text(driver + MUTANTS.get(variant, ""), encoding="utf-8")
        (directory / "conftest.py").write_text(REPORTER, encoding="utf-8")
        selection = "test_scpi_learner.py" + (f"::{target}" if target else "")
        command = [sys.executable, "-m", "pytest", selection, "-q", "--tb=short",
                   "-c", "pytest.ini", "--strict-markers", "-p", "no:cacheprovider"]
        if marker:
            command += ["-m", marker]
        environment = os.environ.copy()
        environment.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="",
                           PYTHONDONTWRITEBYTECODE="1")
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTEST_PLUGINS", None)
        completed = subprocess.run(command, cwd=directory, env=environment, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=5)
        output = completed.stdout + completed.stderr
        report = directory / "events.json"
        assert report.exists(), f"Nested pytest could not report its results:\n{output}"
        result = json.loads(report.read_text(encoding="utf-8"))
        result.update(returncode=completed.returncode, output=output)
        cache[key] = result
        return result

    try:
        yield run
    finally:
        temporary.cleanup()


# Probe bodies first so unfinished exercises fail with NotImplementedError.
@pytest.fixture(scope="module")
def number_ready() -> None:
    number_test("0", 0.0)


@pytest.fixture(scope="module")
def error_ready() -> None:
    error_test('0,"No error"', (0, "No error"))


@pytest.fixture(scope="module")
def sweep_ready() -> None:
    sweep_test()


@pytest.fixture(scope="module")
def quirk_ready() -> None:
    try:
        quirk_test()
    except (AssertionError, pytest.fail.Exception):
        # Desired overload behavior deliberately fails on the supplied firmware.
        pass


def items_for(report: dict[str, Any], name: str) -> list[dict[str, Any]]:
    assert not report["errors"], f"Learner tests could not be collected: {report['output']}"
    return [item for item in report["items"] if item["name"] == name]


def results_for(report: dict[str, Any], name: str) -> list[dict[str, Any]]:
    nodes = {item["nodeid"] for item in items_for(report, name)}
    return [result for result in report["results"] if result["nodeid"] in nodes]


def assert_passed(report: dict[str, Any], name: str) -> None:
    results = results_for(report, name)
    assert results and all(result["outcome"] == "passed" and result["xfail"] is None
                           for result in results), f"{name} must pass on the good driver:\n{report['output']}"


def test_e1_number_formats_pass(number_ready: None, run_driver: Run) -> None:
    report = run_driver()
    name = "test_e1_number_reply"
    assert_passed(report, name)
    items = items_for(report, name)
    assert len(items) >= 6, "Use @pytest.mark.parametrize with at least six rows."
    for reply, expected in NUMBERS:
        assert any(item["params"] == {"reply": reply, "expected": expected} for item in items), (
            f"Missing required number row: {reply!r} -> {expected}"
        )


@pytest.mark.parametrize("variant", ["number-sign", "number-exponent", "number-padding"])
def test_e1_number_tests_catch_mutants(number_ready: None, run_driver: Run, variant: str) -> None:
    report = run_driver(variant, "test_e1_number_reply")
    results = results_for(report, "test_e1_number_reply")
    assert report["returncode"] == 1 and any(result["outcome"] == "failed" for result in results), (
        f"Your number test accepted the {variant} bug; assert the actual parsed value.\n{report['output']}"
    )


def test_e2_error_cases_have_ids(error_ready: None, run_driver: Run) -> None:
    report = run_driver()
    name = "test_e2_error_reply"
    assert_passed(report, name)
    items = items_for(report, name)
    for reply, expected in ERRORS:
        assert any(item["params"] == {"reply": reply, "expected": list(expected)} for item in items), (
            f"Missing required error row: {reply!r} -> {expected!r}"
        )
    ids = [item["id"] for item in items]
    assert all(isinstance(case_id, str) and case_id and case_id.isascii()
               and all(character.isalnum() or character == "-" for character in case_id)
               and any(character.isalpha() for character in case_id) for case_id in ids), (
        "Give each row an explicit readable ASCII id, such as 'queue-clear' (letters, digits, hyphens)."
    )
    assert len(ids) == len(set(ids)), "Give error cases distinct ids."


@pytest.mark.parametrize("variant", ["error-sign", "error-message", "error-comma"])
def test_e2_error_tests_catch_mutants(error_ready: None, run_driver: Run, variant: str) -> None:
    report = run_driver(variant, "test_e2_error_reply")
    results = results_for(report, "test_e2_error_reply")
    assert report["returncode"] == 1 and any(result["outcome"] == "failed" for result in results), (
        f"Your error test accepted the {variant} bug; check both code and full message.\n{report['output']}"
    )


def test_e3_sweep_is_slow_and_checks_channels(sweep_ready: None, run_driver: Run) -> None:
    report = run_driver()
    name = "test_e3_station_sweep"
    assert_passed(report, name)
    items = items_for(report, name)
    assert len(items) == 1 and any(mark["name"] == "slow" for mark in items[0]["marks"]), (
        "Decorate the single sweep test with @pytest.mark.slow."
    )
    broken = run_driver("sweep-channel", name)
    assert broken["returncode"] == 1 and any(result["outcome"] == "failed"
                                             for result in results_for(broken, name)), (
        f"Your sweep must catch a driver that always queries channel 1:\n{broken['output']}"
    )


@pytest.mark.parametrize("variant", ["sweep-validation", "sweep-zero", "sweep-negative"])
def test_e3_sweep_rejects_invalid_channels(sweep_ready: None, run_driver: Run, variant: str) -> None:
    name = "test_e3_station_sweep"
    broken = run_driver(variant, name)
    assert broken["returncode"] == 1 and any(result["outcome"] == "failed"
                                             for result in results_for(broken, name)), (
        "Your sweep must use pytest.raises(ValueError) for both channels 0 and -1; "
        f"it accepted the {variant} bug:\n{broken['output']}"
    )


def test_e3_not_slow_deselects_sweep(sweep_ready: None, run_driver: Run) -> None:
    report = run_driver(marker="not slow")
    assert report["returncode"] in (0, 1), f"The quick run could not execute:\n{report['output']}"
    assert report["deselected"] == ["test_e3_station_sweep"], (
        "-m 'not slow' must deselect only the station sweep."
    )
    assert not items_for(report, "test_e3_station_sweep"), "The slow sweep still ran."
    ordinary = run_driver()
    expected = {item["nodeid"] for item in ordinary["items"]
                if item["name"] != "test_e3_station_sweep"}
    assert {item["nodeid"] for item in report["items"]} == expected, (
        "All nonslow cases must remain selected."
    )


def test_e4_quirk_is_reasoned_xfail(quirk_ready: None, run_driver: Run) -> None:
    report = run_driver()
    name = "test_e4_overload_quirk"
    items = items_for(report, name)
    assert len(items) == 1, "Keep a single overload-quirk test."
    marks = [mark for mark in items[0]["marks"] if mark["name"] == "xfail"]
    assert len(marks) == 1 and marks[0]["kwargs"].get("strict") is True, (
        "Use @pytest.mark.xfail(..., strict=True)."
    )
    reason = marks[0]["kwargs"].get("reason", "")
    assert isinstance(reason, str) and "FW-17" in reason and len(reason) > len("FW-17"), (
        "The xfail reason must name FW-17 and explain its overload bug."
    )
    results = results_for(report, name)
    assert len(results) == 1 and results[0]["outcome"] == "skipped" and results[0]["xfail"], (
        f"The supplied firmware should produce XFAIL, not a pass or ordinary skip:\n{report['output']}"
    )


def test_e4_fixed_firmware_is_strict_xpass(quirk_ready: None, run_driver: Run) -> None:
    report = run_driver("fixed-firmware", "test_e4_overload_quirk")
    results = results_for(report, "test_e4_overload_quirk")
    assert report["returncode"] == 1 and len(results) == 1 and results[0]["outcome"] == "failed" \
        and "XPASS(strict)" in results[0]["detail"], (
            "Assert the desired overload exception: repaired firmware should cause a strict XPASS.\n"
            + report["output"]
        )
