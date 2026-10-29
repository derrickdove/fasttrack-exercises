import pytest

from starter.decide import (
    classify,
    count_failures,
    first_out_of_limits,
    settle_index,
)


@pytest.mark.parametrize(
    "value, expected",
    [(4.0, "LOW"), (5.0, "PASS"), (6.0, "HIGH")],
)
def test_e1_two_limits(value: float, expected: str) -> None:
    got = classify(value, 4.5, 5.5)
    assert got == expected, f"reading {value}: expected {expected}, got {got}"


@pytest.mark.parametrize("value", [4.5, 5.5])
def test_e1_boundaries_pass(value: float) -> None:
    got = classify(value, 4.5, 5.5)
    assert got == "PASS", f"boundary {value} must pass, got {got}"


@pytest.mark.parametrize(
    "value, low, high, expected",
    [
        (-100.0, None, 5.0, "PASS"),
        (6.0, None, 5.0, "HIGH"),
        (100.0, 0.0, None, "PASS"),
        (-1.0, 0.0, None, "LOW"),
        (-100.0, None, None, "PASS"),
        (100.0, None, None, "PASS"),
    ],
)
def test_e1_unbounded_sides(
    value: float, low: float | None, high: float | None, expected: str
) -> None:
    got = classify(value, low, high)
    assert got == expected, f"{value=}, {low=}, {high=}: expected {expected}, got {got}"


@pytest.mark.parametrize(
    "value, low, high, expected",
    [
        (0.25, None, 0.0, "HIGH"),
        (-0.25, 0.0, None, "LOW"),
        (0.0, 0.0, 0.0, "PASS"),
        (-3.0, -2.0, -1.0, "LOW"),
        (-1.0, -2.0, -1.0, "PASS"),
        (0.0, -2.0, -1.0, "HIGH"),
    ],
)
def test_e1_zero_and_negative_limits(
    value: float, low: float | None, high: float | None, expected: str
) -> None:
    got = classify(value, low, high)
    assert got == expected, f"{value=}, {low=}, {high=}: expected {expected}, got {got}"


def test_e2_mixed_batch() -> None:
    got = count_failures([4.0, 4.5, 5.0, 5.5, 6.0], 4.5, 5.5)
    assert got == 2, f"one low and one high reading means 2 failures, got {got}"


@pytest.mark.parametrize("values", [[], [4.5, 5.0, 5.5]])
def test_e2_no_failures(values: list[float]) -> None:
    got = count_failures(values, 4.5, 5.5)
    assert got == 0, f"{values} has no failures, got {got}"


@pytest.mark.parametrize("values", [[4.0, 4.0, 6.0, 6.0], [6.0], [4.0]])
def test_e2_counts_each_failure(values: list[float]) -> None:
    got = count_failures(values, 4.5, 5.5)
    assert got == len(values), f"all {len(values)} readings fail, got {got}"


def test_e2_equal_zero_limits() -> None:
    got = count_failures([-0.25, 0.0, 0.0, 0.25], 0.0, 0.0)
    assert got == 2, f"only the two nonzero readings fail, got {got}"


def test_e2_preserves_collection_order() -> None:
    values = [-1.0, -3.0, 0.0, -2.0]
    original = values.copy()
    got = count_failures(values, -2.0, -1.0)
    assert got == 2, f"negative limits should identify two failures, got {got}"
    assert values == original, "counting failures must leave the readings unchanged"


@pytest.mark.parametrize("value", [4.0, 6.0])
def test_e3_first_reading_fails(value: float) -> None:
    got = first_out_of_limits([value, 5.0, 6.0], 4.5, 5.5)
    assert got == 0, f"first reading fails: expected index 0, got {got}"


@pytest.mark.parametrize(
    "values, expected",
    [([5.0, 5.5, 6.0, 4.0], 2), ([4.5, 4.0, 6.0], 1), ([5.0, 5.0, 4.0], 2)],
)
def test_e3_first_failure_in_order(values: list[float], expected: int) -> None:
    got = first_out_of_limits(values, 4.5, 5.5)
    assert got == expected, f"{values}: expected first failing index {expected}, got {got}"


@pytest.mark.parametrize("values", [[], [4.5, 5.0, 5.5], [5.0]])
def test_e3_no_failure_returns_none(values: list[float]) -> None:
    got = first_out_of_limits(values, 4.5, 5.5)
    assert got is None, f"all readings pass: expected None, got {got}"


def test_e3_equal_zero_limits() -> None:
    got = first_out_of_limits([0.0, 0.0, -0.25, 0.25], 0.0, 0.0)
    assert got == 2, f"zero readings pass: expected first failure at index 2, got {got}"


def test_e3_preserves_collection_order() -> None:
    values = [-1.0, -3.0, -2.0]
    original = values.copy()
    got = first_out_of_limits(values, -2.0, -1.0)
    assert got == 1, f"expected negative reading failure at index 1, got {got}"
    assert values == original, "finding a failure must leave readings unchanged"


@pytest.mark.parametrize(
    "values, hold, expected",
    [
        ([5.0, 5.0, 5.0, 6.0], 3, 0),
        ([0.0, 4.75, 5.25, 5.0, 6.0], 3, 1),
        ([0.0, 5.0, 5.0, 5.0, 5.0], 2, 1),
        ([0.0, 0.0, 5.0, 5.0], 2, 2),
        ([5.0, 5.0], 2, 0),
    ],
)
def test_e4_returns_earliest_run_start(
    values: list[float], hold: int, expected: int
) -> None:
    got = settle_index(values, 5.0, 0.25, hold)
    assert got == expected, f"{values}, {hold=}: expected start {expected}, got {got}"


@pytest.mark.parametrize(
    "values, expected",
    [
        ([5.0, 6.0, 5.0, 5.0, 5.0], 2),
        ([5.0, 4.0, 5.0, 5.0, 6.0, 5.0, 5.0, 5.0], 5),
        ([5.0, 6.0, 5.0, 6.0, 5.0], None),
    ],
)
def test_e4_bad_reading_breaks_run(values: list[float], expected: int | None) -> None:
    got = settle_index(values, 5.0, 0.25, 3)
    assert got == expected, f"{values}: need 3 adjacent good readings, got {got}"


@pytest.mark.parametrize(
    "values, hold",
    [([], 1), ([5.0, 5.0], 3), ([0.0, 6.0, 4.0], 1), ([0.0, 5.0, 5.0], 3)],
)
def test_e4_incomplete_run_returns_none(values: list[float], hold: int) -> None:
    got = settle_index(values, 5.0, 0.25, hold)
    assert got is None, f"{values}, {hold=}: no complete run, expected None, got {got}"


@pytest.mark.parametrize(
    "values, target, tolerance, hold, expected",
    [
        ([4.75, 5.25], 5.0, 0.25, 2, 0),
        ([4.5, 5.5, 5.0], 5.0, 0.25, 1, 2),
        ([-2.25, -1.75], -2.0, 0.25, 2, 0),
        ([-0.25, 0.25], 0.0, 0.25, 2, 0),
        ([4.75, 5.0, 5.0, 5.25], 5.0, 0.0, 2, 1),
    ],
)
def test_e4_tolerance_boundaries_and_zero(
    values: list[float], target: float, tolerance: float, hold: int, expected: int
) -> None:
    got = settle_index(values, target, tolerance, hold)
    assert got == expected, f"{values}, {target=}, {tolerance=}: expected {expected}, got {got}"


def test_e4_preserves_collection_order() -> None:
    values = [6.0, 5.0, 4.0, 5.0, 5.0]
    original = values.copy()
    got = settle_index(values, 5.0, 0.25, 2)
    assert got == 3, f"expected first complete run at index 3, got {got}"
    assert values == original, "settling checks must leave readings unchanged"
