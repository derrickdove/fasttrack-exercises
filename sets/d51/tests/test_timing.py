"""Scripted timing checks and one concept check per speed question; no sleeps."""

from collections.abc import Callable

import pytest

from starter.timing import measure, meets_deadline, speed_answers


SPEED_ANSWERS = {"Q1": "B", "Q2": "C", "Q3": "A"}


def is_correct(answers: dict[str, str], question: str) -> bool:
    return answers.get(question) == SPEED_ANSWERS[question]


def scripted_clock(values: list[float]) -> Callable[[], float]:
    ticks = iter(values)
    return lambda: next(ticks)


@pytest.mark.parametrize(
    "ticks, runs, expected",
    [
        ([0.0, 0.125, 1.0, 1.5, 2.0, 2.25, 3.0, 4.0], 4,
         {"min": 125.0, "median": 375.0, "p99": 1000.0, "max": 1000.0}),
        ([0.0, 0.125, 1.0, 1.5, 2.0, 2.25], 3,
         {"min": 125.0, "median": 250.0, "p99": 500.0, "max": 500.0}),
        ([5.0, 5.125], 1,
         {"min": 125.0, "median": 125.0, "p99": 125.0, "max": 125.0}),
        ([1.0, 1.0, 2.0, 2.0], 2,
         {"min": 0.0, "median": 0.0, "p99": 0.0, "max": 0.0}),
        ([0.0, 0.0009765625, 1.0, 1.0009765625], 2,
         {"min": 0.9765625, "median": 0.9765625, "p99": 0.9765625, "max": 0.9765625}),
    ],
)
def test_e5_summaries_in_milliseconds(
    ticks: list[float], runs: int, expected: dict[str, float]
) -> None:
    got = measure(lambda: object(), runs, scripted_clock(ticks))
    assert got == expected, f"for clock ticks {ticks}, expected {expected}, got {got}"


def test_e5_clock_brackets_each_call() -> None:
    events: list[str] = []
    ticks = iter([0.0, 0.125, 1.0, 1.25, 2.0, 2.5])

    def clock() -> float:
        events.append("clock")
        return next(ticks)

    def step() -> object:
        events.append("step")
        return object()

    stats = measure(step, 3, clock)
    assert events == ["clock", "step", "clock"] * 3, "time each call separately, exactly runs times"
    assert stats["max"] == 500.0, "exclude gaps between calls from step durations"


@pytest.mark.parametrize("runs, expected_p99", [(100, 99000.0), (101, 100000.0), (200, 198000.0), (201, 199000.0)])
def test_e5_p99_uses_sorted_nearest_rank(runs: int, expected_p99: float) -> None:
    ticks: list[float] = []
    now = 0.0
    for duration in range(runs, 0, -1):
        ticks.extend([now, now + duration])
        now += duration + 1.0
    stats = measure(lambda: None, runs, scripted_clock(ticks))
    assert stats["p99"] == expected_p99, "sort the durations and use ceil(0.99 * n) - 1"
    assert stats["max"] == runs * 1000.0, "p99 need not equal the maximum for a large sample"


@pytest.mark.parametrize("runs", [0, -1, -100])
def test_e5_invalid_runs_do_not_call_callbacks(runs: int) -> None:
    events: list[str] = []

    def step() -> None:
        events.append("step")

    def clock() -> float:
        events.append("clock")
        return 0.0

    with pytest.raises(ValueError):
        measure(step, runs, clock)
    assert events == [], "reject runs below 1 before touching either callback"


@pytest.mark.parametrize("failure_at", ["step", "start_clock", "end_clock"])
def test_e5_callback_exception_propagates_without_retry(failure_at: str) -> None:
    events: list[str] = []
    failure = TimeoutError("timing callback failed")

    def step() -> None:
        events.append("step")
        if failure_at == "step":
            raise failure

    def clock() -> float:
        events.append("clock")
        if failure_at == "start_clock" or (failure_at == "end_clock" and len(events) == 3):
            raise failure
        return 0.0

    with pytest.raises(TimeoutError) as caught:
        measure(step, 3, clock)
    assert caught.value is failure, "preserve the callback's original exception"
    expected_events = {
        "step": ["clock", "step"],
        "start_clock": ["clock"],
        "end_clock": ["clock", "step", "clock"],
    }
    assert events == expected_events[failure_at], "stop immediately when a callback raises"


@pytest.mark.parametrize(
    "stats, deadline, expected",
    [
        ({"min": 1.0, "median": 1.0, "p99": 1.0, "max": 50.0}, 10.0, False),
        ({"min": 125.0, "median": 375.0, "p99": 1000.0, "max": 1000.0}, 1000.0, True),
        ({"min": 125.0, "median": 375.0, "p99": 1000.0, "max": 1000.0}, 999.0, False),
        ({"max": 0.0}, 0.0, True),
        ({"max": 0.5}, 1.0, True),
        ({"max": 0.5}, 0.25, False),
    ],
)
def test_e5_deadline_uses_inclusive_maximum(
    stats: dict[str, float], deadline: float, expected: bool
) -> None:
    original = stats.copy()
    assert meets_deadline(stats, deadline) is expected, "compare max with the deadline, including equality"
    assert stats == original, "keep the caller's timing summary unchanged"


def test_e6_q1_language_choice() -> None:
    answers = speed_answers()
    assert set(answers) == {"Q1", "Q2", "Q3"}, "Q1: reread E6 Contract for the required question keys"
    correct = is_correct(answers, "Q1")
    assert correct, "Q1: reread E6, Language choice, and Debugging: checking assumptions"


def test_e6_q2_hot_loop() -> None:
    correct = is_correct(speed_answers(), "Q2")
    assert correct, "Q2: reread E6, A slow loop, and Debugging: isolating the cause"


def test_e6_q3_station_evidence() -> None:
    correct = is_correct(speed_answers(), "Q3")
    assert correct, "Q3: reread E6, Timing evidence, and the time.perf_counter reading"
