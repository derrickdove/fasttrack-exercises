"""Block 5 execution through TestStep, RunResult, and run_sequence only."""

from dataclasses import fields, is_dataclass
from enum import Enum

import pytest


def test_run_state_is_enum_with_contract_names(executor):
    assert issubclass(executor.RunState, Enum)
    assert {state.name for state in executor.RunState} == {
        "IDLE", "SETUP", "RUNNING", "PASS", "FAIL", "ERROR", "ABORTED",
    }


def test_test_step_is_dataclass_with_optional_callbacks(executor):
    run = lambda: []
    step = executor.TestStep(name="read bus", run=run)
    assert is_dataclass(step)
    assert [field.name for field in fields(step)] == ["name", "run", "setup", "teardown"]
    assert (step.name, step.run, step.setup, step.teardown) == ("read bus", run, None, None)


def test_run_result_is_dataclass_with_contract_fields(executor):
    result = executor.RunResult(state=executor.RunState.IDLE, results=[], log=[])
    assert is_dataclass(result)
    assert [field.name for field in fields(result)] == ["state", "results", "log"]
    assert (result.state, result.results, result.log) == (executor.RunState.IDLE, [], [])


def test_steps_run_in_order_and_teardowns_run_in_reverse_at_end(executor, recorded_step):
    events = []
    steps = [recorded_step(name, events) for name in ["power", "read", "verify"]]
    executor.run_sequence(steps, {})
    assert events == [
        "power:setup", "power:run", "read:setup", "read:run", "verify:setup", "verify:run",
        "verify:teardown", "read:teardown", "power:teardown",
    ], "cleanup must wait until all setup/run pairs finish, then unwind in reverse"


def test_step_without_setup_still_runs_its_teardown(executor, models, bus_limits):
    events = []
    def run():
        events.append("run")
        return [models.Measurement("bus_voltage", 24.0, "V")]
    steps = [executor.TestStep("read", run, teardown=lambda: events.append("off"))]
    result = executor.run_sequence(steps, bus_limits)
    assert events == ["run", "off"]
    assert result.state == executor.RunState.PASS


def test_all_steps_measurements_go_through_check_all(executor, models, themis):
    limits = {name: models.Limit(name, 22.0, 30.0, "V") for name in ["z_rail", "b_rail"]}
    groups = [
        [models.Measurement("z_rail", 24.0, "V"), models.Measurement("a_extra", 24.0, "V")],
        [models.Measurement("z_rail", 25.0, "V"), models.Measurement("b_rail", 21.0, "V")],
    ]
    steps = [executor.TestStep("first", lambda: groups[0]), executor.TestStep("second", lambda: groups[1])]
    result = executor.run_sequence(steps, limits)
    expected = themis.check_all(groups[0] + groups[1], limits)
    assert result.results == expected, "collect readings across steps before checking, including duplicates"
    assert result.state == executor.RunState.ERROR


@pytest.mark.parametrize("value,expected", [(24.0, "PASS"), (31.0, "FAIL"), (float("nan"), "ERROR")],
                         ids=["pass", "fail", "check-error"])
def test_final_state_matches_overall(executor, models, bus_limits, value, expected):
    step = executor.TestStep("read", lambda: [models.Measurement("bus_voltage", value, "V")])
    result = executor.run_sequence([step], bus_limits)
    assert result.state == executor.RunState[expected]
    assert len(result.results) == 1
    assert result.results[0].status.name == expected


def test_no_steps_and_no_limits_is_error(executor):
    result = executor.run_sequence([], {})
    assert result.results == []
    assert result.state == executor.RunState.ERROR


@pytest.mark.parametrize("phase", ["setup", "run"])
def test_setup_or_run_exception_skips_rest_but_cleans_started_steps(executor, recorded_step, phase):
    events = []
    steps = [recorded_step("power", events), recorded_step("bad", events, fail_at=phase),
             recorded_step("skipped", events)]
    result = executor.run_sequence(steps, {})
    prefix = ["power:setup", "power:run", "bad:setup"]
    if phase == "run":
        prefix.append("bad:run")
    assert events == prefix + ["bad:teardown", "power:teardown"]
    assert result.state == executor.RunState.ERROR


@pytest.mark.parametrize("phase", ["setup", "run"])
def test_keyboard_interrupt_aborts_without_reraising_and_cleans_up(executor, recorded_step, phase):
    events = []
    steps = [recorded_step("power", events),
             recorded_step("abort", events, fail_at=phase, error=KeyboardInterrupt()),
             recorded_step("skipped", events)]
    result = executor.run_sequence(steps, {})
    prefix = ["power:setup", "power:run", "abort:setup"]
    if phase == "run":
        prefix.append("abort:run")
    assert events == prefix + ["abort:teardown", "power:teardown"]
    assert result.state == executor.RunState.ABORTED


@pytest.mark.parametrize("value", [24.0, 31.0], ids=["would-pass", "would-fail"])
def test_teardown_exception_changes_pass_or_fail_to_error(executor, recorded_step, bus_limits, value):
    events = []
    step = recorded_step("read", events, fail_at="teardown", value=value)
    result = executor.run_sequence([step], bus_limits)
    assert result.state == executor.RunState.ERROR
    assert events == ["read:setup", "read:run", "read:teardown"]
    assert len(result.results) == 1, "keep the measurement result when cleanup fails"


@pytest.mark.parametrize("failure,expected", [(None, "ERROR"), (RuntimeError("read failed"), "ERROR"),
                                              (KeyboardInterrupt(), "ABORTED")],
                         ids=["normal-run", "run-error", "abort"])
def test_one_teardown_failure_does_not_prevent_remaining_cleanup(
    executor, recorded_step, failure, expected,
):
    events = []
    steps = [recorded_step("power", events), recorded_step("bad_cleanup", events, fail_at="teardown")]
    if failure is not None:
        steps.append(recorded_step("last", events, fail_at="run", error=failure))
    result = executor.run_sequence(steps, {})
    cleanup = [event for event in events if event.endswith(":teardown")]
    assert cleanup == (["last:teardown"] if failure is not None else []) + [
        "bad_cleanup:teardown", "power:teardown",
    ]
    assert result.state == executor.RunState[expected]


def test_log_records_state_transitions_and_step_events(executor, recorded_step, bus_limits):
    result = executor.run_sequence([recorded_step("bus_read", [])], bus_limits)
    assert isinstance(result.log, list)
    transitions = [line for line in result.log if not line.startswith("step ")]
    assert transitions and transitions[0] == "IDLE->SETUP"
    assert "SETUP->RUNNING" in transitions
    current = "IDLE"
    for line in transitions:
        source, target = line.split("->")
        assert source == current, f"transition {line!r} must start at the previous state"
        assert source in executor.RunState.__members__ and target in executor.RunState.__members__
        current = target
    assert current == result.state.name == "PASS"
    events = [line for line in result.log if line.startswith("step ")]
    assert events and all(line.startswith("step bus_read: ") and line.removeprefix("step bus_read: ")
                          for line in events)
