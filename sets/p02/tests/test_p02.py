import pytest

from starter.decisions import (
    bug_answers,
    channel_numbers,
    checked_channel_numbers,
    count_over_limit,
    first_over_limit,
    is_in_range,
    is_over_limit,
    pass_or_fail,
    reading_band,
    steps_to_target,
    total_readings,
)


def _message(call: str, expected: object, got: object) -> str:
    message = f"{call}: expected {expected!r}, got {got!r}."
    if got is None:
        message += " your function returned None: did you forget `return`? Use return, not print."
    return message


@pytest.mark.parametrize(
    "reading, limit, expected",
    [(6.0, 5.0, True), (5.0, 5.0, False), (4.0, 5.0, False),
     (0.0, 0.0, False), (-1.0, -2.0, True)],
)
def test_e1_compare_reading(reading: float, limit: float, expected: bool) -> None:
    got = is_over_limit(reading, limit)
    assert got is expected, _message(f"is_over_limit({reading!r}, {limit!r})", expected, got)


@pytest.mark.parametrize(
    "reading, limit, expected",
    [(6.0, 5.0, "FAIL"), (5.0, 5.0, "PASS"), (4.0, 5.0, "PASS"),
     (0.0, 0.0, "PASS"), (-1.0, -2.0, "FAIL")],
)
def test_e2_pass_or_fail(reading: float, limit: float, expected: str) -> None:
    got = pass_or_fail(reading, limit)
    assert got == expected, _message(f"pass_or_fail({reading!r}, {limit!r})", expected, got)


@pytest.mark.parametrize(
    "reading, low, high, expected",
    [(3.0, 4.0, 6.0, "LOW"), (4.0, 4.0, 6.0, "OK"),
     (5.0, 4.0, 6.0, "OK"), (6.0, 4.0, 6.0, "OK"),
     (7.0, 4.0, 6.0, "HIGH"), (0.0, 0.0, 0.0, "OK")],
)
def test_e3_reading_band(reading: float, low: float, high: float, expected: str) -> None:
    got = reading_band(reading, low, high)
    call = f"reading_band({reading!r}, {low!r}, {high!r})"
    assert got == expected, _message(call, expected, got)


@pytest.mark.parametrize(
    "reading, low, high, expected",
    [(3.0, 4.0, 6.0, False), (4.0, 4.0, 6.0, True),
     (5.0, 4.0, 6.0, True), (6.0, 4.0, 6.0, True),
     (7.0, 4.0, 6.0, False), (0.0, 0.0, 0.0, True)],
)
def test_e4_inclusive_range(reading: float, low: float, high: float, expected: bool) -> None:
    got = is_in_range(reading, low, high)
    call = f"is_in_range({reading!r}, {low!r}, {high!r})"
    assert got is expected, _message(call, expected, got)


@pytest.mark.parametrize(
    "readings, expected",
    [([1.5, 2.0, 0.5], 4.0), ([3.0], 3.0), ([], 0.0),
     ([2.0, 2.0, 2.0], 6.0), ([-1.0, 2.5, 0.5], 2.0)],
)
def test_e5_running_total(readings: list[float], expected: float) -> None:
    got = total_readings(readings)
    assert got == expected, _message(f"total_readings({readings!r})", expected, got)


def test_e5_leaves_readings_unchanged() -> None:
    readings = [3.0, 1.0, 2.0]
    got = total_readings(readings)
    call = "total_readings([3.0, 1.0, 2.0])"
    assert got == 6.0, _message(call, 6.0, got)
    assert readings == [3.0, 1.0, 2.0], _message(
        call + " input list after the call", [3.0, 1.0, 2.0], readings
    )


@pytest.mark.parametrize(
    "readings, limit, expected",
    [([4.0, 7.0, 8.0], 5.0, 2), ([5.0, 5.0], 5.0, 0),
     ([], 5.0, 0), ([7.0, 7.0, 7.0], 5.0, 3),
     ([7.0], 5.0, 1), ([4.0], 5.0, 0)],
)
def test_e6_counter(readings: list[float], limit: float, expected: int) -> None:
    got = count_over_limit(readings, limit)
    call = f"count_over_limit({readings!r}, {limit!r})"
    assert type(got) is int, _message(call, "a whole-number count (int)", got)
    assert got == expected, _message(call, expected, got)


def test_e6_leaves_readings_unchanged() -> None:
    readings = [8.0, 4.0, 7.0]
    got = count_over_limit(readings, 5.0)
    call = "count_over_limit([8.0, 4.0, 7.0], 5.0)"
    assert type(got) is int, _message(call, "a whole-number count (int)", got)
    assert got == 2, _message(call, 2, got)
    assert readings == [8.0, 4.0, 7.0], _message(
        call + " input list after the call", [8.0, 4.0, 7.0], readings
    )


@pytest.mark.parametrize(
    "readings, limit, expected",
    [([4.0, 7.0, 9.0], 5.0, 7.0), ([8.0, 7.0], 5.0, 8.0),
     ([4.0, 5.0, 6.0], 5.0, 6.0), ([7.0], 5.0, 7.0),
     ([0.0, 1.0], -1.0, 0.0)],
)
def test_e7_first_failing_value(readings: list[float], limit: float, expected: float) -> None:
    got = first_over_limit(readings, limit)
    assert got == expected, _message(f"first_over_limit({readings!r}, {limit!r})", expected, got)


@pytest.mark.parametrize("readings", [[4.0, 5.0], [5.0], []])
def test_e7_no_failure(readings: list[float]) -> None:
    got = first_over_limit(readings, 5.0)
    assert got is None, _message(f"first_over_limit({readings!r}, 5.0)", None, got)


def test_e7_leaves_readings_unchanged() -> None:
    readings = [4.0, 8.0, 7.0]
    got = first_over_limit(readings, 5.0)
    call = "first_over_limit([4.0, 8.0, 7.0], 5.0)"
    assert got == 8.0, _message(call, 8.0, got)
    assert readings == [4.0, 8.0, 7.0], _message(
        call + " input list after the call", [4.0, 8.0, 7.0], readings
    )


@pytest.mark.parametrize(
    "n, expected", [(3, [1, 2, 3]), (1, [1]), (0, []), (5, [1, 2, 3, 4, 5])],
)
def test_e8_channel_numbers(n: int, expected: list[int]) -> None:
    got = channel_numbers(n)
    assert got == expected, _message(f"channel_numbers({n!r})", expected, got)


@pytest.mark.parametrize(
    "target, step, expected",
    [(2.0, 0.5, 4), (2.5, 1.0, 3), (0.0, 0.5, 0),
     (0.25, 0.5, 1), (1.0, 1.0, 1), (1.25, 0.25, 5), (5.0, 2.0, 3)],
)
def test_e9_voltage_steps(target: float, step: float, expected: int) -> None:
    got = steps_to_target(target, step)
    call = f"steps_to_target({target!r}, {step!r})"
    assert type(got) is int, _message(call, "a whole-number count (int)", got)
    assert got == expected, _message(call, expected, got)


@pytest.mark.parametrize(
    "count, expected", [(2, [1, 2]), (0, []), (1, [1]), (4, [1, 2, 3, 4])],
)
def test_e10_valid_counts(count: int, expected: list[int]) -> None:
    got = checked_channel_numbers(count)
    assert got == expected, _message(f"checked_channel_numbers({count!r})", expected, got)


@pytest.mark.parametrize("count", [-1, -3])
def test_e10_rejects_negative_count(count: int) -> None:
    try:
        got = checked_channel_numbers(count)
    except ValueError:
        return
    assert False, (
        f"checked_channel_numbers({count!r}): expected a raised ValueError, got {got!r}. "
        "Check the guard: the `if` and the `raise ValueError(...)` line."
    )


_BUG_ANSWERS = {"Q1": "C", "Q2": "A", "Q3": "B"}
_BUG_HINTS = {
    "Q1": "Reread E1: storing a value and comparing values use different symbols.",
    "Q2": "Reread E8: range excludes its stop value.",
    "Q3": "Reread E5: return ends the function, even when it is inside a loop.",
}


def test_e11_answer_format() -> None:
    got = bug_answers()
    assert isinstance(got, dict), _message("bug_answers()", "a dictionary of Q1 through Q3", got)
    keys = list(got)
    assert keys == ["Q1", "Q2", "Q3"], _message(
        "list(bug_answers())", ["Q1", "Q2", "Q3"], keys
    )


@pytest.mark.parametrize("question", ["Q1", "Q2", "Q3"])
def test_e11_bug_choices(question: str) -> None:
    got = bug_answers()
    assert isinstance(got, dict), _message("bug_answers()", "a dictionary of answer letters", got)
    if question not in got:
        pytest.fail(
            f"bug_answers() {question}: this question is missing from your answers. "
            "Add its key with your chosen uppercase option letter.",
            pytrace=False,
        )
    answer = got[question]
    if answer != _BUG_ANSWERS[question]:
        pytest.fail(
            f"bug_answers() {question}: submitted choice {answer!r}. Hint: {_BUG_HINTS[question]}",
            pytrace=False,
        )
