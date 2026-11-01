"""Behavior checks for station transitions, callbacks, and cleanup."""

import pytest

from starter.sequencer import TRANSITIONS, Sequencer, Step, can_move, run_steps


EXPECTED = {
    "IDLE": {"SETUP", "ERROR", "ABORTED"},
    "SETUP": {"RUNNING", "ERROR", "ABORTED"},
    "RUNNING": {"PASS", "FAIL", "ERROR", "ABORTED"},
    "PASS": set(),
    "FAIL": set(),
    "ERROR": set(),
    "ABORTED": set(),
}


@pytest.fixture
def events() -> list[str]:
    return []


def station_step(
    events: list[str],
    name: str,
    *,
    passed: bool = True,
    failure_phase: str | None = None,
    error: type[BaseException] = RuntimeError,
) -> Step:
    """Create fake instrument callbacks with an optional injected failure."""
    def record(phase: str) -> None:
        events.append(f"{name}.{phase}")
        if phase == failure_phase:
            raise error(f"{name}: {phase} failed")

    def setup() -> None:
        record("setup")

    def run() -> bool:
        record("run")
        return passed

    def teardown() -> None:
        record("teardown")

    return setup, run, teardown


def test_e1_transition_table() -> None:
    # Exercise the stub first, so unfinished E1 reports NotImplementedError.
    assert can_move("IDLE", "SETUP"), "a station must be able to begin setup"
    assert TRANSITIONS == EXPECTED, "supply exactly the seven states and their allowed destinations"
    assert all(isinstance(targets, set) for targets in TRANSITIONS.values())


def test_e1_every_known_transition() -> None:
    for source, destinations in EXPECTED.items():
        for target in EXPECTED:
            expected = target in destinations
            assert can_move(source, target) is expected, f"wrong permission for {source} -> {target}"
    assert TRANSITIONS == EXPECTED, "checking moves must not alter the transition table"


@pytest.mark.parametrize("source,target", [
    ("UNKNOWN", "ERROR"), ("IDLE", "unknown"), ("idle", "SETUP"),
    ("", "ABORTED"), ("RUNNING", "pass"), ("ERROR", "IDLE"),
])
def test_e1_unknown_and_terminal_moves(source: str, target: str) -> None:
    assert can_move(source, target) is False, f"{source!r} -> {target!r} must be rejected"


@pytest.mark.parametrize("terminal", ["PASS", "FAIL", "ERROR", "ABORTED"])
def test_e2_records_legal_path(terminal: str) -> None:
    station = Sequencer()
    assert station.state == "IDLE" and station.history == ["IDLE"]
    for target in ("SETUP", "RUNNING", terminal):
        assert station.move(target) is None, "move changes the station and returns None"
    assert station.state == terminal
    assert station.history == ["IDLE", "SETUP", "RUNNING", terminal]


@pytest.mark.parametrize("target", ["RUNNING", "PASS", "IDLE", "idle", "UNKNOWN", ""])
def test_e2_rejected_move_preserves_state(target: str) -> None:
    station = Sequencer()
    with pytest.raises(ValueError):
        station.move(target)
    assert station.state == "IDLE", "a rejected move must leave state unchanged"
    assert station.history == ["IDLE"], "a rejected move must not enter history"
    station.move("SETUP")
    with pytest.raises(ValueError):
        station.move("PASS")
    assert station.state == "SETUP" and station.history == ["IDLE", "SETUP"]


@pytest.mark.parametrize("terminal", ["ERROR", "ABORTED"])
def test_e2_emergency_moves_and_terminal_lock(terminal: str) -> None:
    station = Sequencer()
    station.move(terminal)
    for target in EXPECTED:
        with pytest.raises(ValueError):
            station.move(target)
    assert station.state == terminal
    assert station.history == ["IDLE", terminal], "terminal states cannot be restarted or changed"


def test_e2_instances_have_separate_history() -> None:
    first, second = Sequencer(), Sequencer()
    first.move("SETUP")
    assert second.state == "IDLE" and second.history == ["IDLE"]
    assert first.history is not second.history, "each station owns its history"


def test_e3_all_setups_then_runs_then_reverse_cleanup(events: list[str]) -> None:
    steps = [station_step(events, name) for name in ("supply", "meter", "load")]
    result = run_steps(steps)
    assert result == ("PASS", ["IDLE", "SETUP", "RUNNING", "PASS"])
    assert events == [
        "supply.setup", "meter.setup", "load.setup",
        "supply.run", "meter.run", "load.run",
        "load.teardown", "meter.teardown", "supply.teardown",
    ], f"wrong station operation order: {events}"


def test_e3_empty_station_sequence() -> None:
    assert run_steps([]) == ("PASS", ["IDLE", "SETUP", "RUNNING", "PASS"])


def test_e3_failed_measurement_stops_runs_but_cleans_all(events: list[str]) -> None:
    steps = [station_step(events, "supply"), station_step(events, "meter", passed=False),
             station_step(events, "load")]
    assert run_steps(steps) == ("FAIL", ["IDLE", "SETUP", "RUNNING", "FAIL"])
    assert events == [
        "supply.setup", "meter.setup", "load.setup", "supply.run", "meter.run",
        "load.teardown", "meter.teardown", "supply.teardown",
    ], "a failed measurement skips later runs, but not their registered cleanup"


@pytest.mark.parametrize("failed_index", [0, 1, 2])
def test_e3_setup_error_cleans_even_partial_setup(events: list[str], failed_index: int) -> None:
    steps = [station_step(events, str(index), failure_phase="setup" if index == failed_index else None)
             for index in range(3)]
    assert run_steps(steps) == ("ERROR", ["IDLE", "SETUP", "ERROR"])
    expected = [f"{index}.setup" for index in range(failed_index + 1)]
    expected += [f"{index}.teardown" for index in reversed(range(failed_index + 1))]
    assert events == expected, "clean only attempted setups, including the setup that raised"


def test_e3_run_error_stops_measurements_and_cleans_all(events: list[str]) -> None:
    steps = [station_step(events, "supply", failure_phase="run", error=ValueError),
             station_step(events, "meter")]
    assert run_steps(steps) == ("ERROR", ["IDLE", "SETUP", "RUNNING", "ERROR"])
    assert events == ["supply.setup", "meter.setup", "supply.run", "meter.teardown", "supply.teardown"]


def test_e3_calls_are_independent_and_input_is_preserved(events: list[str]) -> None:
    steps = [station_step(events, "meter")]
    saved = steps.copy()
    first = run_steps(steps)
    second = run_steps(steps)
    assert steps == saved, "run_steps must not consume or reorder the input list"
    assert first == second == ("PASS", ["IDLE", "SETUP", "RUNNING", "PASS"])
    assert first[1] is not second[1], "each run needs a fresh history"
    assert events == ["meter.setup", "meter.run", "meter.teardown"] * 2


@pytest.mark.parametrize("failed_index", [0, 1, 2])
def test_e4_setup_interrupt_still_cleans_partial_setup(events: list[str], failed_index: int) -> None:
    steps = [station_step(events, str(index), failure_phase="setup" if index == failed_index else None,
                          error=KeyboardInterrupt) for index in range(3)]
    assert run_steps(steps) == ("ABORTED", ["IDLE", "SETUP", "ABORTED"])
    expected = [f"{index}.setup" for index in range(failed_index + 1)]
    expected += [f"{index}.teardown" for index in reversed(range(failed_index + 1))]
    assert events == expected, "Ctrl+C during setup must not leave attempted instruments open"


def test_e4_run_interrupt_stops_runs_and_cleans_all(events: list[str]) -> None:
    steps = [station_step(events, "supply"),
             station_step(events, "meter", failure_phase="run", error=KeyboardInterrupt),
             station_step(events, "load")]
    assert run_steps(steps) == ("ABORTED", ["IDLE", "SETUP", "RUNNING", "ABORTED"])
    assert events == [
        "supply.setup", "meter.setup", "load.setup", "supply.run", "meter.run",
        "load.teardown", "meter.teardown", "supply.teardown",
    ]


@pytest.mark.parametrize("prior_result", ["PASS", "FAIL", "ERROR", "ABORTED"])
@pytest.mark.parametrize("cleanup_error", [RuntimeError, KeyboardInterrupt])
def test_e4_cleanup_error_wins_over_selected_result(
    events: list[str], prior_result: str, cleanup_error: type[BaseException],
) -> None:
    measurement_error = KeyboardInterrupt if prior_result == "ABORTED" else RuntimeError
    first = station_step(events, "supply", passed=prior_result != "FAIL",
                         failure_phase="run" if prior_result in {"ERROR", "ABORTED"} else None,
                         error=measurement_error)
    steps = [first, station_step(events, "meter"),
             station_step(events, "load", failure_phase="teardown", error=cleanup_error)]
    assert run_steps(steps) == ("ERROR", ["IDLE", "SETUP", "RUNNING", "ERROR"])
    expected = ["supply.setup", "meter.setup", "load.setup", "supply.run"]
    if prior_result == "PASS":
        expected += ["meter.run", "load.run"]
    expected += ["load.teardown", "meter.teardown", "supply.teardown"]
    assert events == expected, "cleanup must continue after a teardown raises"


def test_e4_multiple_cleanup_failures_do_not_skip_remaining_cleanup(events: list[str]) -> None:
    steps = [station_step(events, "supply"),
             station_step(events, "meter", failure_phase="teardown", error=KeyboardInterrupt),
             station_step(events, "load", failure_phase="teardown", error=ValueError)]
    assert run_steps(steps) == ("ERROR", ["IDLE", "SETUP", "RUNNING", "ERROR"])
    assert events == [
        "supply.setup", "meter.setup", "load.setup", "supply.run", "meter.run", "load.run",
        "load.teardown", "meter.teardown", "supply.teardown",
    ]


def test_e4_setup_abort_with_cleanup_failure_finishes_error(events: list[str]) -> None:
    steps = [station_step(events, "supply", failure_phase="teardown"),
             station_step(events, "meter", failure_phase="setup", error=KeyboardInterrupt),
             station_step(events, "load")]
    assert run_steps(steps) == ("ERROR", ["IDLE", "SETUP", "ERROR"])
    assert events == ["supply.setup", "meter.setup", "meter.teardown", "supply.teardown"]
