"""Run each learner test against the correct checker and its targeted mutants."""
from collections.abc import Callable
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from starter.test_limits_learner import (
    test_e1_inclusive_bounds as inclusive_bounds,
    test_e2_missing_reading as missing_reading,
    test_e3_nan_reading as nan_reading,
    test_e4_reversed_limits as reversed_limits,
)

SET_DIR = Path(__file__).resolve().parents[1]


def _check_case(tmp_path: Path, case: Callable[[], None], mutant: str | None = None) -> None:
    # Run on the real library first: unfinished bodies retain NotImplementedError
    # in the outer report instead of being mistaken for a caught mutant.
    case()
    package = tmp_path / "starter"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    shutil.copyfile(SET_DIR / "starter" / "test_limits_learner.py", package / "test_limits_learner.py")
    library = SET_DIR / "starter" / "limits_lib.py"
    if mutant is not None:
        library = SET_DIR / "tests" / "mutants" / mutant
    shutil.copyfile(library, package / "limits_lib.py")
    report = tmp_path / "result.xml"
    env = os.environ.copy()
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="",
               PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(tmp_path))
    env.pop("PYTEST_PLUGINS", None)
    command = [sys.executable, "-m", "pytest",
               f"starter/test_limits_learner.py::{case.__name__}",
               "-q", "--tb=short", "-p", "no:cacheprovider",
               "--rootdir", str(tmp_path), "--confcutdir", str(tmp_path),
               "--junitxml", str(report)]
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=10)
    output = result.stdout + result.stderr
    assert report.exists(), f"The learner test process did not produce a report:\n{output}"
    cases = ET.parse(report).findall(".//testcase")
    assert cases, f"No learner test was collected:\n{output}"
    assert not any(item.find("error") is not None or item.find("skipped") is not None
                   for item in cases), f"Fix test errors or skips before checking faults:\n{output}"
    failures = sum(item.find("failure") is not None for item in cases)
    if mutant is None:
        assert result.returncode == 0 and failures == 0, f"Correct checker must pass:\n{output}"
    else:
        assert result.returncode == 1 and failures > 0, (
            f"{case.__name__} let fault {mutant} pass. Add an assertion for its contract.\n{output}"
        )


def test_e1_correct_checker(tmp_path: Path) -> None:
    _check_case(tmp_path, inclusive_bounds)


@pytest.mark.parametrize("mutant", [
    "e1_below_passes.py",
    "e1_exclusive_bounds.py",
    "e1_inside_low.py",
    "e1_upper_exclusive.py",
    "e1_above_passes.py",
    "e1_equal_low.py",
])
def test_e1_catches_required_cases(tmp_path: Path, mutant: str) -> None:
    _check_case(tmp_path, inclusive_bounds, mutant)


def test_e2_correct_checker(tmp_path: Path) -> None:
    _check_case(tmp_path, missing_reading)


@pytest.mark.parametrize("mutant", [
    "e2_missing_passes.py",
    "e2_missing_negative.py",
])
def test_e2_catches_required_cases(tmp_path: Path, mutant: str) -> None:
    _check_case(tmp_path, missing_reading, mutant)


def test_e3_correct_checker(tmp_path: Path) -> None:
    _check_case(tmp_path, nan_reading)


@pytest.mark.parametrize("mutant", [
    "e3_nan_passes.py",
    "e3_nan_negative.py",
])
def test_e3_catches_required_cases(tmp_path: Path, mutant: str) -> None:
    _check_case(tmp_path, nan_reading, mutant)


def test_e4_correct_checker(tmp_path: Path) -> None:
    _check_case(tmp_path, reversed_limits)


@pytest.mark.parametrize("mutant", [
    "e4_swapped_limits.py",
    "e4_missing_first.py",
    "e4_nan_first.py",
])
def test_e4_catches_required_cases(tmp_path: Path, mutant: str) -> None:
    _check_case(tmp_path, reversed_limits, mutant)
