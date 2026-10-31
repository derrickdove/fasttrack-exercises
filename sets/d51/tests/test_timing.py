"""Scripted timing and graded bench diagnosis; no hardware or sleeps."""

from collections.abc import Callable
import hashlib

import pytest

from starter.timing import diagnose_captures, measure, meets_deadline


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


# Store answer digests (fixed-length fingerprints), not readable answer values.
# Compare inside a helper, then assert only booleans: pytest must not reveal the key.
ANSWER_DIGESTS: dict[str, dict[str, set[str]]] = {
    "fault": {
        "case_a": {"f0e2f943dcf2fd296b5e47b6905c593b505ef45b6bc524b15774af4580878810"},
        "case_b": {"021b4e899f3cda42fa480819603ed5b6f42adbaaa3d25827fde1bf934a021bbb"},
    },
    "serial_evidence": {
        "case_a": {"bbe97d17449c6e005ff7bd18e03aa67b690bb365d0d1d6fca22879aeba7ad488"},
        "case_b": {"39a6c3d9fd987246f99377af29b499c7e6ce5f1c10893aad7f4b88db9a0bb089"},
    },
    "dmm_evidence": {
        "case_a": {"779c533a14725b9b679aaf9ca3c7b8a3365495afb1ed2d842289c1d7dfec2bca"},
        "case_b": {"f29bc501c32a5bee77970d9927f9bc63038089ea29da0d765dc8aa5bba90d3fa"},
    },
    "scope_evidence": {
        "case_a": {"b23280c959e5c753fbbff7854a72ed8124d2b0ae9e8fca6b23b346722da23e44"},
        "case_b": {"2d12e99ea10566aeb91543d4b95f4b91709551dd3eab66c2216e26b382f89229", "ec2cb38a3c7f3280d04e2da585c6ca37028cbd0135bada2a591ff4d564bd8aa5"},
    },
    "next_measurement": {
        "case_a": {"0ac0890568e1a7a537d884fcff2baeb7e87023ed59fbab245ddb5526111815e5"},
        "case_b": {"77dd02dbcb94cb91ac0d4163ec165854543e062dfe373c29c48525a3f0f0aa68"},
    },
    "disposition": {
        "case_a": {"7f745488a79260b7e16b168c3229e58196132a3d413d033944a9a42359c5cfc4"},
        "case_b": {"2f91eb47d524563a3b6a75367c8037a881fadaa928c70469e5e77f37c66a2c7f"},
    },
}


def field_is_correct(answers: object, field: str) -> bool:
    __tracebackhide__ = True
    if not isinstance(answers, dict):
        return False
    for case in ("case_a", "case_b"):
        diagnosis = answers.get(case)
        if not isinstance(diagnosis, dict):
            return False
        value = diagnosis.get(field)
        if not isinstance(value, str):
            return False
        if hashlib.sha256(value.encode("utf-8")).hexdigest() not in ANSWER_DIGESTS[field][case]:
            return False
    return True


def test_e6_answer_shape() -> None:
    answers = diagnose_captures()
    assert isinstance(answers, dict), "E6: return a dictionary; reread Contract"
    assert set(answers) == {"case_a", "case_b"}, "E6: provide both captured cases"
    fields = {
        "fault", "serial_evidence", "dmm_evidence", "scope_evidence",
        "next_measurement", "disposition",
    }
    for diagnosis in answers.values():
        assert isinstance(diagnosis, dict), "E6: each case needs a dictionary"
        assert set(diagnosis) == fields, "E6: use exactly the six documented fields"
        assert all(isinstance(value, str) for value in diagnosis.values()), "E6: values must be strings"


def test_e6_fault_from_independent_evidence() -> None:
    correct = field_is_correct(diagnose_captures(), "fault")
    assert correct, "E6: compare raw units, reported volts, and independent scope evidence"


def test_e6_serial_evidence_at_the_event() -> None:
    correct = field_is_correct(diagnose_captures(), "serial_evidence")
    assert correct, "E6: cite each serial exchange at the load-switch event"


def test_e6_independent_measurement_evidence() -> None:
    answers = diagnose_captures()
    correct = field_is_correct(answers, "dmm_evidence") and field_is_correct(answers, "scope_evidence")
    assert correct, "E6: cite each DMM row and the scope row specified by the evidence contract"


def test_e6_distinguishing_next_measurement() -> None:
    correct = field_is_correct(diagnose_captures(), "next_measurement")
    assert correct, "E6: choose a next measurement that separates report scaling from a physical dip"


def test_e6_safe_disposition() -> None:
    correct = field_is_correct(diagnose_captures(), "disposition")
    assert correct, "E6: match the hold action to the evidence; neither case supports release"
