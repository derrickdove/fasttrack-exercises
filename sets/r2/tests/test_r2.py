"""Public checks for the weekly station review; do not edit these tests."""
import gc
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import weakref

import pytest

from starter.review2 import (
    current_in_amps, load_limit_bands, rolling_bad_counts, station_readiness, summarize,
)


@pytest.mark.parametrize("value,unit,expected", [
    (2.0, "A", 2.0), (250.0, "mA", 0.25), (12.0, "uA", 0.000012),
    (-5.0, "mA", -0.005), (0.0, "uA", 0.0),
])
def test_e1_units(value: float, unit: str, expected: float) -> None:
    assert current_in_amps(value, unit) == pytest.approx(expected), "check the scale into amperes"


@pytest.mark.parametrize("unit", ["a", "MA", " mA", "mA ", "V", ""])
def test_e1_unknown_unit(unit: str) -> None:
    with pytest.raises(ValueError):
        current_in_amps(1.0, unit)


def test_e1_mypy(tmp_path: Path) -> None:
    # Reach the exercise stub first, so an untouched E1 reports NotImplementedError.
    current_in_amps(0.0, "A")
    module = Path(__file__).resolve().parents[1] / "starter/review2.py"
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "--follow-imports=skip",
         "--cache-dir", str(tmp_path / "mypy-cache"), str(module)],
        cwd=tmp_path, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, "E1: keep review2.py typed. Mypy says:\n" + result.stdout + result.stderr


@pytest.mark.parametrize("statuses,counts,overall", [
    (["PASS", "FAIL", "PASS", "ERROR"], {"PASS": 2, "FAIL": 1, "ERROR": 1}, "ERROR"),
    (["FAIL", "PASS", "FAIL"], {"PASS": 1, "FAIL": 2, "ERROR": 0}, "FAIL"),
    (["PASS"], {"PASS": 1, "FAIL": 0, "ERROR": 0}, "PASS"),
    ([], {"PASS": 0, "FAIL": 0, "ERROR": 0}, "NOT_RUN"),
])
def test_e2_summary(statuses: list[str], counts: dict[str, int], overall: str) -> None:
    assert summarize(statuses) == (counts, overall), "include zero counts and choose the worst result"


@pytest.mark.parametrize("statuses", [["SKIP"], ["pass"], ["PASS", ""], ["PASS", "ERROR "]])
def test_e2_invalid_status(statuses: list[str]) -> None:
    with pytest.raises(ValueError):
        summarize(statuses)


def test_e2_does_not_change_input() -> None:
    statuses = ["FAIL", "PASS", "ERROR"]
    before = statuses.copy()
    counts, _ = summarize(statuses)
    assert statuses == before, "reporting must preserve the source results"
    counts["FAIL"] = 999
    assert summarize(statuses)[0]["FAIL"] == 1, "each report needs its own counts dictionary"


@pytest.mark.parametrize("statuses,window,expected", [
    (["PASS", "FAIL", "ERROR", "PASS", "PASS"], 3, [2, 2, 1]),
    (["PASS", "ERROR", "FAIL"], 1, [0, 1, 1]),
    (["PASS", "FAIL"], 2, [1]), (["PASS"], 2, []), ([], 1, []),
])
def test_e3_windows(statuses: list[str], window: int, expected: list[int]) -> None:
    assert rolling_bad_counts(iter(statuses), window) == expected, "emit only full windows; accept an iterator"


@pytest.mark.parametrize("window", [0, -1, -20])
def test_e3_reject_window_before_consuming(window: int) -> None:
    source = iter(["PASS", "FAIL"])
    with pytest.raises(ValueError):
        rolling_bad_counts(source, window)
    assert next(source) == "PASS", "validate window before asking the source for readings"


@pytest.mark.parametrize("statuses,window", [(["unknown"], 10), (["PASS", "FAIL", "pass"], 2)])
def test_e3_unknown_status(statuses: list[str], window: int) -> None:
    with pytest.raises(ValueError):
        rolling_bad_counts(iter(statuses), window)


def test_e3_bounded_storage() -> None:
    # Weak references track input lifetimes without keeping the strings alive.
    class TrackedStatus(str):
        pass

    window = 32
    retained = weakref.WeakValueDictionary[int, TrackedStatus]()

    def statuses():
        for i in range(4096):
            status = TrackedStatus("FAIL" if i % 4 == 0 else "PASS")
            retained[i] = status
            yield status
            if i % 512 == 511:
                # Also release unreachable cycles on runtimes without immediate collection.
                gc.collect()
                assert len(retained) <= 4 * window, (
                    f"retained {len(retained)} input strings for window {window}; "
                    "keep only O(window) input, not the entire iterable"
                )

    assert rolling_bad_counts(statuses(), window) == [8] * (4096 - window + 1)


def test_e3_fast_enough() -> None:
    started = time.perf_counter()
    got = rolling_bad_counts(("FAIL" if i % 5 == 0 else "PASS" for i in range(200_000)), 5000)
    elapsed = time.perf_counter() - started
    assert len(got) == 195_001 and all(count == 1000 for count in got), "every full window contains 1000 failures"
    assert elapsed < 2.0, f"{elapsed:.3f}s: keep a deque and a running count rather than recounting each window"


# Independent good helpers: the learner's tests are copied unchanged next to these.
GOOD_HELPERS = '''import logging
import math


def current_status(value: float, low: float, high: float) -> str:
    if not all(math.isfinite(number) for number in (value, low, high)):
        raise ValueError("current and limits must be finite")
    if low > high:
        raise ValueError("low must not exceed high")
    if value < low:
        return "LOW"
    if value > high:
        return "HIGH"
    return "PASS"


def log_status(logger: logging.Logger, channel: str, status: str) -> None:
    level = logging.WARNING if status == "FAIL" else logging.INFO
    logger.log(level, "%s: %s", channel, status)
'''

MUTANTS = {
    "lower-bound": GOOD_HELPERS.replace("if value < low:", "if value <= low:"),
    "upper-bound": GOOD_HELPERS.replace("if value > high:", "if value >= high:"),
    "reversed-limits": GOOD_HELPERS.replace(
        '    if low > high:\n        raise ValueError("low must not exceed high")\n', ""),
    "nonfinite": GOOD_HELPERS.replace(
        '    if not all(math.isfinite(number) for number in (value, low, high)):\n        raise ValueError("current and limits must be finite")\n', ""),
    "log-level": GOOD_HELPERS.replace('logging.WARNING if status == "FAIL" else logging.INFO', "logging.INFO"),
    "log-channel": GOOD_HELPERS.replace('logger.log(level, "%s: %s", channel, status)', 'logger.log(level, "%s", status)'),
    "log-duplicate": GOOD_HELPERS.replace(
        '    logger.log(level, "%s: %s", channel, status)',
        '    logger.log(level, "%s: %s", channel, status)\n    logger.log(level, "%s: %s", channel, status)'),
}

# Record actual exceptions, rather than treating an import error as catching a bug.
CHILD_PLUGIN = '''import json
from pathlib import Path
import pytest

state = {"failures": [], "skips": 0, "errors": [], "collected": 0}

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.skipped or hasattr(report, "wasxfail"):
        state["skips"] += 1
    if report.failed:
        state["failures"].append({
            "exception": call.excinfo.type.__name__ if call.excinfo else "unknown",
            "phase": report.when,
            "message": str(call.excinfo.value) if call.excinfo else "unknown",
        })

@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector):
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        state["errors"].append(str(report.longrepr))

def pytest_sessionfinish(session, exitstatus):
    state["collected"] = session.testscollected
    Path("outcomes.json").write_text(json.dumps(state), encoding="utf-8")
'''


def run_learner(tmp_path: Path, exercise: int, variant: str) -> tuple[int, dict, str]:
    (tmp_path / "starter").mkdir()
    (tmp_path / "starter/__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "starter/review2.py").write_text(
        GOOD_HELPERS if variant == "good" else MUTANTS[variant], encoding="utf-8")
    source = Path(__file__).resolve().parents[1] / "starter/test_review2_learner.py"
    shutil.copyfile(source, tmp_path / "test_review2_learner.py")
    (tmp_path / "_outcomes.py").write_text(CHILD_PLUGIN, encoding="utf-8")
    env = os.environ.copy()
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="", PYTHONPATH=str(tmp_path),
               PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "test_review2_learner.py", "-k", f"test_e{exercise}_",
         "-p", "_outcomes", "-q", "--rootdir", str(tmp_path), "-o", "addopts="],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=8,
    )
    output = result.stdout + result.stderr
    report_file = tmp_path / "outcomes.json"
    assert report_file.exists(), "The learner test run did not finish:\n" + output
    report = json.loads(report_file.read_text(encoding="utf-8"))
    for failure in report["failures"]:
        if failure["exception"] == "NotImplementedError":
            raise NotImplementedError(f"E{exercise}: replace the learner-test stub: {failure['message']}")
    assert not report["errors"], "Fix learner test imports or syntax:\n" + output
    assert report["collected"] > 0, f"Keep test names starting with test_e{exercise}_"
    assert report["skips"] == 0, "These checks must run: do not skip or mark xfail"
    return result.returncode, report, output


def test_e4_good_implementation(tmp_path: Path) -> None:
    code, report, output = run_learner(tmp_path, 4, "good")
    assert code == 0 and not report["failures"], "Your E4 tests must accept the correct helper:\n" + output


@pytest.mark.parametrize("mutant", ["lower-bound", "upper-bound", "reversed-limits", "nonfinite"])
def test_e4_catches_mutants(tmp_path: Path, mutant: str) -> None:
    code, report, output = run_learner(tmp_path, 4, mutant)
    assert code == 1 and report["failures"], f"E4 tests missed {mutant}: add a contract-based case.\n{output}"
    assert all(failure["phase"] == "call" and failure["exception"] in ("AssertionError", "Failed")
               for failure in report["failures"]), "Catch the defect with an assertion or pytest.raises:\n" + output


def test_e5_good_implementation(tmp_path: Path) -> None:
    code, report, output = run_learner(tmp_path, 5, "good")
    assert code == 0 and not report["failures"], "Your E5 tests must accept the correct helper:\n" + output


@pytest.mark.parametrize("mutant", ["log-level", "log-channel", "log-duplicate"])
def test_e5_catches_mutants(tmp_path: Path, mutant: str) -> None:
    code, report, output = run_learner(tmp_path, 5, mutant)
    assert code == 1 and report["failures"], f"E5 tests missed {mutant}: inspect record level, text and count.\n{output}"
    assert all(failure["phase"] == "call" for failure in report["failures"]), (
        "Catch the logging defect during the test, not setup or teardown:\n" + output
    )


@pytest.fixture
def limit_csv(tmp_path: Path) -> Path:
    path = tmp_path / "station-limits.csv"
    path.write_text(
        'channel,low,high\nBUS_V,27,29\n\n" capteur,rétour ",-2.5,0\nI7,0,0\nbus_v,1e-3,2e-3\n',
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("use_string", [False, True])
def test_e6_load_bands(limit_csv: Path, use_string: bool) -> None:
    before = limit_csv.read_bytes()
    path = str(limit_csv) if use_string else limit_csv
    expected = {"BUS_V": (27.0, 29.0), " capteur,rétour ": (-2.5, 0.0),
                "I7": (0.0, 0.0), "bus_v": (0.001, 0.002)}
    assert load_limit_bands(path) == expected, "read numeric tuples, blank lines and quoted channel text"
    assert limit_csv.read_bytes() == before, "loading limits must not change the source file"


def test_e6_header_only(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("channel,low,high\n\n", encoding="utf-8")
    assert load_limit_bands(path) == {}, "a valid header without records has no bands"


def test_e6_later_band_wins(tmp_path: Path) -> None:
    path = tmp_path / "updated.csv"
    path.write_text("channel,low,high\nBUS_V,27,29\nBUS_V,26,30\n", encoding="utf-8")
    assert load_limit_bands(path) == {"BUS_V": (26.0, 30.0)}, "keep the last band for a repeated channel"


@pytest.mark.parametrize("low,high", [("bad", "2"), ("0", "bad"), ("", "1"), ("0", "")])
def test_e6_invalid_number(tmp_path: Path, low: str, high: str) -> None:
    path = tmp_path / "bad-number.csv"
    path.write_text(f"channel,low,high\nI7,{low},{high}\nI7,0,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_limit_bands(path)


@pytest.mark.parametrize("rows", ["I7,2,1\n", "I7,2,1\nI7,0,2\n", "I7,0,2\nI7,2,1\n"])
def test_e6_reversed_limits(tmp_path: Path, rows: str) -> None:
    path = tmp_path / "reversed.csv"
    path.write_text("channel,low,high\n" + rows, encoding="utf-8")
    with pytest.raises(ValueError):
        load_limit_bands(path)


def test_e6_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_limit_bands(tmp_path / "absent.csv")


@pytest.mark.parametrize("reply,expected", [
    ("1", "READY"), ("0", "BUSY"), (" 1\r\n", "READY"), ("\t0 \n", "BUSY"),
])
def test_e7_readiness_reply(reply: str, expected: str) -> None:
    calls: list[str] = []

    def query(command: str) -> str:
        calls.append(command)
        return reply

    assert station_readiness(query) == expected, "map only the two readiness flag replies"
    assert calls == ["STAT:READY?"], "send the exact command once, with no retry"


@pytest.mark.parametrize("reply", ["", " \r\n", "01", "2", "ready", "1,0"])
def test_e7_invalid_reply(reply: str) -> None:
    calls: list[str] = []

    def query(command: str) -> str:
        calls.append(command)
        return reply

    with pytest.raises(ValueError):
        station_readiness(query)
    assert calls == ["STAT:READY?"], "a malformed reply must not trigger another query"


class LinkTimeout(TimeoutError):
    pass


class CommandRejected(RuntimeError):
    pass


@pytest.mark.parametrize("error", [TimeoutError("silent link"), LinkTimeout("late link")])
def test_e7_timeout_is_offline(error: TimeoutError) -> None:
    calls: list[str] = []

    def query(command: str) -> str:
        calls.append(command)
        raise error

    assert station_readiness(query) == "OFFLINE", "catch TimeoutError and its subclasses"
    assert calls == ["STAT:READY?"], "a timeout returns OFFLINE without retrying"


@pytest.mark.parametrize("error", [CommandRejected("command rejected"), ValueError("bad command"),
                                  OSError("broken link"), TypeError("bad driver")])
def test_e7_other_errors_propagate(error: Exception) -> None:
    calls: list[str] = []

    def query(command: str) -> str:
        calls.append(command)
        raise error

    with pytest.raises(type(error)) as caught:
        station_readiness(query)
    assert caught.value is error, "preserve the original non-timeout exception object"
    assert calls == ["STAT:READY?"], "other failures must stop after the first call"
