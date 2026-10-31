from pathlib import Path
import shlex
from typing import Any

import pytest
import yaml

from starter.review_fix import failed_channels, within_limits
from starter.driver_review import review_answers


@pytest.mark.parametrize("value, expected", [(24.0, True), (21.0, False), (27.0, False)])
def test_e1_voltage_range(value: float, expected: bool) -> None:
    got = within_limits(value, 22.0, 26.0)
    assert got is expected, f"22..26 V at {value}: expected {expected}, got {got}"


@pytest.mark.parametrize("value", [22.0, 26.0])
def test_e1_inclusive_endpoints(value: float) -> None:
    assert within_limits(value, 22.0, 26.0) is True, "Both endpoints must pass"


@pytest.mark.parametrize("value, expected", [(-2.0, True), (-2.1, False), (-1.9, False)])
def test_e1_single_point_limit(value: float, expected: bool) -> None:
    assert within_limits(value, -2.0, -2.0) is expected, "Equal bounds accept exactly that value"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_e1_nonfinite_reading(value: float) -> None:
    assert within_limits(value, 22.0, 26.0) is False, "Non-finite instrument readings must fail"


@pytest.mark.parametrize("readings", [{}, {"bus_b": 26.0, "bus_a": 22.0}])
def test_e2_no_failures(readings: dict[str, float]) -> None:
    assert failed_channels(readings, 22.0, 26.0) == [], "Empty or all-passing input has no failures"


def test_e2_late_failure() -> None:
    readings = {"bus_a": 24.0, "bus_b": 28.0}
    assert failed_channels(readings, 22.0, 26.0) == ["bus_b"], "Do not return after the first channel"


def test_e2_all_failures_sorted() -> None:
    readings = {"bus_z": 29.0, "bus_a": 20.0, "bus_m": 24.0}
    got = failed_channels(readings, 22.0, 26.0)
    assert got == ["bus_a", "bus_z"], f"Expected every failure in name order, got {got}"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_e2_nonfinite_channel(value: float) -> None:
    got = failed_channels({"bus_a": 24.0, "bus_b": value}, 22.0, 26.0)
    assert got == ["bus_b"], "A non-finite reading must appear in the failure list"


def test_e2_preserves_input() -> None:
    readings = {"bus_z": 28.0, "bus_a": 24.0}
    before = list(readings.items())
    first = failed_channels(readings, 22.0, 26.0)
    first.append("operator-note")
    assert list(readings.items()) == before, "Do not change readings or its insertion order"
    assert failed_channels(readings, 22.0, 26.0) == ["bus_z"], "Return a fresh list on each call"


@pytest.fixture
def workflow() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "starter" / "ci.yml"
    parsed = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    if parsed == {"__exercise_stub__": "E3: write the GitHub Actions workflow"}:
        raise NotImplementedError("E3: replace the supplied ci.yml placeholder")
    assert isinstance(parsed, dict), "ci.yml must contain a YAML mapping"
    return parsed


@pytest.fixture
def steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict), "Add a jobs mapping"
    checks = jobs.get("checks")
    assert isinstance(checks, dict), "Add the station job named checks"
    assert checks.get("runs-on") == "ubuntu-latest", "checks must run on ubuntu-latest"
    assert "if" not in checks, "The checks job must run without an if condition"
    assert not checks.get("continue-on-error", False), "The checks job must propagate failures"
    supplied = checks.get("steps")
    assert isinstance(supplied, list) and supplied, "checks needs a nonempty steps list"
    assert all(isinstance(step, dict) for step in supplied), "Each step must be a YAML mapping"
    assert all("if" not in step and not step.get("continue-on-error", False) for step in supplied), (
        "Station checks must run unconditionally and propagate failures"
    )
    for scope in [workflow, checks, *supplied]:
        assert "working-directory" not in scope, "Do not override the working directory"
        defaults = scope.get("defaults", {}).get("run", {})
        assert "working-directory" not in defaults, "Do not override the default working directory"
    return supplied


def _action_position(steps: list[dict[str, Any]], action: str) -> int:
    for index, step in enumerate(steps):
        used = step.get("uses", "")
        if isinstance(used, str) and used.startswith(action + "@") and used.split("@", 1)[1]:
            return index
    pytest.fail(f"Add a uses: {action}@<version> step")


def _commands(steps: list[dict[str, Any]], tool: str) -> list[tuple[int, list[str]]]:
    found = []
    for index, step in enumerate(steps):
        run = step.get("run", "")
        assert isinstance(run, str), "run must be shell command text"
        commands = [shlex.split(line, comments=True) for line in run.splitlines()]
        commands = [words for words in commands if words]
        if len(commands) != 1:
            continue
        words = commands[0]
        if words[:2] in (["python", "-m"], ["python3", "-m"]):
            words = words[2:]
        if words and words[0] == tool:
            found.append((index, words[1:]))
    return found


def test_e3_push_and_pull_request(workflow: dict[str, Any]) -> None:
    # PyYAML's YAML 1.1 rules read an unquoted `on` key as the boolean True.
    events = workflow.get("on", workflow.get(True))
    assert isinstance(events, (list, dict)), "Use an event list or mapping for on"
    assert "push" in events and "pull_request" in events, "Run on push and pull_request"
    if isinstance(events, dict):
        assert all(events[event] in (None, {}) for event in ("push", "pull_request")), (
            "Do not filter push or pull_request events in this exercise"
        )


def test_e3_checkout_before_python(steps: list[dict[str, Any]]) -> None:
    checkout = _action_position(steps, "actions/checkout")
    setup = _action_position(steps, "actions/setup-python")
    assert checkout < setup, "Check out the station code before setting up Python"


def test_e3_python_312(steps: list[dict[str, Any]]) -> None:
    setup = steps[_action_position(steps, "actions/setup-python")]
    options = setup.get("with", {})
    assert isinstance(options, dict), "setup-python needs a with mapping"
    assert options.get("python-version") == "3.12", "Quote python-version: '3.12' as text"


def test_e3_install_requirements(steps: list[dict[str, Any]]) -> None:
    installs = [index for index, args in _commands(steps, "pip")
                if args == ["install", "-r", "requirements.txt"]]
    setup = _action_position(steps, "actions/setup-python")
    assert any(index > setup for index in installs), "After setup, run pip install -r requirements.txt"


def test_e3_pytest_and_mypy_after_install(steps: list[dict[str, Any]]) -> None:
    installs = [index for index, args in _commands(steps, "pip")
                if args == ["install", "-r", "requirements.txt"]]
    tests = [index for index, args in _commands(steps, "pytest") if args == ["sets/d40"]]
    types = [index for index, args in _commands(steps, "mypy")
             if args == ["--strict", "sets/d40/starter"]]
    assert tests, "Run pytest sets/d40 as a direct command"
    assert types, "Run mypy --strict sets/d40/starter as a direct command"
    assert any(install < test < check for install in installs for test in tests for check in types), (
        "Use separate steps in this order: install, pytest, mypy"
    )


# Keep keyed answers out of traceback source lines and assertion introspection.
_REVIEW_KEYS = {
    "Q1": ("drivers/bus_probe.py", 14, "C", "B", True, "D"),
    "Q2": ("drivers/bus_probe.py", 15, "A", "D", False, "B"),
    "Q3": ("drivers/bus_probe.py", 18, "D", "A", True, "A"),
}
_REVIEW_FIELDS = {
    "file", "line", "consequence", "regression_test", "repair_fixed", "repair_reason", "comment",
}


@pytest.fixture
def review() -> list[dict[str, Any]]:
    answers = review_answers()
    if not isinstance(answers, list) or len(answers) != 3:
        pytest.fail("E4: return three findings; reread E4 Return contract", pytrace=False)
    locations = set()
    for finding in answers:
        if not isinstance(finding, dict) or set(finding) != _REVIEW_FIELDS:
            pytest.fail("E4: use every specified field; reread E4 Return contract", pytrace=False)
        if not isinstance(finding["file"], str) or not finding["file"].strip():
            pytest.fail("E4: supply a file path; reread E4 Return contract", pytrace=False)
        if type(finding["line"]) is not int or finding["line"] < 1:
            pytest.fail("E4: use a positive integer line; reread E4 Diff primer", pytrace=False)
        location = (finding["file"], finding["line"])
        if location in locations:
            pytest.fail("E4: use distinct defect locations; reread E4 Return contract", pytrace=False)
        locations.add(location)
        for field in ("consequence", "regression_test", "repair_reason"):
            if not isinstance(finding[field], str) or finding[field] not in ("A", "B", "C", "D"):
                pytest.fail("E4: choose one A-D letter per option field; reread E4 Review choices", pytrace=False)
        if type(finding["repair_fixed"]) is not bool:
            pytest.fail("E4: repair_fixed must be a bool; reread E4 Return contract", pytrace=False)
        if not isinstance(finding["comment"], str) or len(finding["comment"].split()) < 12:
            pytest.fail("E4: explain your review in at least 12 words; reread E4 Return contract", pytrace=False)
    return answers


def _check_review(review: list[dict[str, Any]], question: str) -> None:
    expected = _REVIEW_KEYS[question]
    matched = next((finding for finding in review
                    if (finding["file"], finding["line"]) == expected[:2]), None)
    if matched is None:
        pytest.fail(f"{question}: reread E4 Diff primer and Station contract; recheck defect anchors", pytrace=False)
    actual = tuple(matched[field] for field in
                   ("file", "line", "consequence", "regression_test", "repair_fixed", "repair_reason"))
    if actual != expected:
        pytest.fail(f"{question}: reread E4 Station contract and Review choices; trace both diffs again", pytrace=False)


def test_e4_review_structure(review: list[dict[str, Any]]) -> None:
    # The fixture checks fields, types, unique anchors, and comment length.
    if not review:
        pytest.fail("E4: reread E4 Return contract", pytrace=False)


def test_e4_q1_review(review: list[dict[str, Any]]) -> None:
    _check_review(review, "Q1")


def test_e4_q2_review(review: list[dict[str, Any]]) -> None:
    _check_review(review, "Q2")


def test_e4_q3_review(review: list[dict[str, Any]]) -> None:
    _check_review(review, "Q3")
