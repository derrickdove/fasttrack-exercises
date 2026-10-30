from collections.abc import Iterator
from time import perf_counter
from typing import overload

import pytest

from starter.windows import (
    dedupe_keep_order,
    first_spike,
    max_in_windows,
    rolling_mean,
)


class _CountedFloat(float):
    """Count additions on readings even after their container is copied."""

    def __new__(cls, value: float, additions: list[int]) -> "_CountedFloat":
        sample = super().__new__(cls, value)
        sample.additions = additions
        return sample

    def __add__(self, other: float) -> float:
        self.additions[0] += 1
        return float.__add__(self, other)

    def __radd__(self, other: float) -> float:
        return self + other


class _ReadBudget(list[float]):
    """Count sample accesses, including samples copied by a slice."""

    def __init__(self, values: list[float]) -> None:
        super().__init__(values)
        self.reads = 0
        self.limit = 12 * len(values) + 12

    def _spend(self, count: int) -> None:
        self.reads += count
        assert self.reads <= self.limit, (
            f"Read more than {self.limit} samples for {len(self)} inputs; "
            "update saved state instead of rescanning each window"
        )

    def __iter__(self) -> Iterator[float]:
        for value in super().__iter__():
            self._spend(1)
            yield value

    @overload
    def __getitem__(self, index: int) -> float: ...

    @overload
    def __getitem__(self, index: slice) -> list[float]: ...

    def __getitem__(self, index: int | slice) -> float | list[float]:
        if isinstance(index, slice):
            self._spend(len(range(*index.indices(len(self)))))
        else:
            self._spend(1)
        return super().__getitem__(index)


@pytest.mark.parametrize(
    "values,window,expected",
    [
        ([2.0, 4.0, 8.0, 10.0], 2, [3.0, 6.0, 9.0]),
        ([0.1, 0.2, 0.3, 0.4], 3, [0.2, 0.3]),
        ([-4.0, 2.0, -1.0, 5.0], 2, [-1.0, 0.5, 2.0]),
        ([7.5, -2.0], 1, [7.5, -2.0]),
        ([1.0, 2.0, 6.0], 3, [3.0]),
        ([5.0], 1, [5.0]),
        ([5.0], 2, []),
        ([], 1, []),
    ],
)
def test_e1_full_windows(
    values: list[float], window: int, expected: list[float]
) -> None:
    got = rolling_mean(values, window)
    assert got == pytest.approx(expected), f"wrong means for {values}, window={window}"


@pytest.mark.parametrize("window", [0, -1, -100])
@pytest.mark.parametrize("values", [[], [1.0, 2.0]])
def test_e1_invalid_window(values: list[float], window: int) -> None:
    with pytest.raises(ValueError):
        rolling_mean(values, window)


@pytest.mark.parametrize("window", [1, 2, 5])
def test_e1_preserves_input(window: int) -> None:
    values = [3.0, 1.0, 4.0]
    before = values.copy()
    got = rolling_mean(values, window)
    assert values == before, "the recorded sensor trace must stay unchanged"
    assert got is not values, "return a new list even when window=1"


def test_e1_linear_sample_work() -> None:
    plain = [float(index % 17) for index in range(6000)]
    additions = [0]
    values = _ReadBudget([_CountedFloat(value, additions) for value in plain])
    expected = [sum(plain[start:start + 300]) / 300 for start in range(5701)]
    got = rolling_mean(values, 300)
    assert got == pytest.approx(expected), "the running total must slide one sample at a time"
    limit = 12 * len(plain) + 12
    assert additions[0] <= limit, (
        f"Used {additions[0]} additions for {len(plain)} inputs (limit {limit}); "
        "reuse the total instead of summing each window, even after copying the input"
    )


def test_e1_fast_enough() -> None:
    values = [float(index % 1000) for index in range(200_000)]
    start = perf_counter()
    got = rolling_mean(values, 1000)
    elapsed = perf_counter() - start
    assert got == pytest.approx([499.5] * 199_001), "one mean is needed per full window"
    assert elapsed <= 2.0, f"rolling_mean took {elapsed:.3f}s; reuse the previous total (limit 2s)"


@pytest.mark.parametrize(
    "values,window,expected",
    [
        ([4.0, 2.0, 3.0, 1.0, 5.0], 3, [4.0, 3.0, 5.0]),
        ([1.0, 2.0, 3.0, 4.0], 2, [2.0, 3.0, 4.0]),
        ([4.0, 3.0, 2.0, 1.0], 2, [4.0, 3.0, 2.0]),
        ([8.0, 8.0, 1.0, 2.0], 2, [8.0, 8.0, 2.0]),
        ([-4.0, -2.0, -7.0, -1.0], 2, [-2.0, -2.0, -1.0]),
        ([2.0, 2.0, 2.0], 2, [2.0, 2.0]),
        ([2.5, -1.0], 1, [2.5, -1.0]),
        ([1.0, 9.0, 3.0], 3, [9.0]),
        ([5.0], 1, [5.0]),
        ([5.0], 2, []),
        ([], 4, []),
    ],
)
def test_e2_full_windows(
    values: list[float], window: int, expected: list[float]
) -> None:
    got = max_in_windows(values, window)
    assert got == expected, f"wrong maxima for {values}, window={window}"


@pytest.mark.parametrize("window", [0, -1, -100])
@pytest.mark.parametrize("values", [[], [1.0, 2.0]])
def test_e2_invalid_window(values: list[float], window: int) -> None:
    with pytest.raises(ValueError):
        max_in_windows(values, window)


@pytest.mark.parametrize("window", [1, 2, 5])
def test_e2_preserves_input(window: int) -> None:
    values = [3.0, 1.0, 4.0]
    before = values.copy()
    got = max_in_windows(values, window)
    assert values == before, "the recorded sensor trace must stay unchanged"
    assert got is not values, "return a new list even when window=1"


@pytest.mark.parametrize("descending", [False, True])
def test_e2_linear_sample_work(descending: bool) -> None:
    plain = [float((index * 37) % 503) for index in range(6000)]
    if descending:
        plain = [float(6000 - index) for index in range(6000)]
    values = _ReadBudget(plain)
    expected = [max(plain[start:start + 300]) for start in range(5701)]
    got = max_in_windows(values, 300)
    assert got == expected, "discard expired and dominated candidates, preserving the maximum"


def test_e2_fast_enough() -> None:
    values = [float(200_000 - index) for index in range(200_000)]
    start = perf_counter()
    got = max_in_windows(values, 1000)
    elapsed = perf_counter() - start
    assert got == values[:199_001], "on a decreasing trace the leftmost sample is the maximum"
    assert elapsed <= 2.0, f"max_in_windows took {elapsed:.3f}s; use a deque (limit 2s)"


@pytest.mark.parametrize(
    "values,window,factor,expected",
    [
        ([2.0, 2.0, 4.0, 9.0], 2, 2.0, 3),
        ([2.0, 2.0, 5.0, 100.0], 2, 2.0, 2),
        ([100.0, 1.0, 1.0, 3.0], 2, 2.0, 3),
        ([10.0, 10.0, 1.0, 1.0, 4.0, 99.0], 2, 2.0, 4),
        ([0.0, 0.0, 0.0, 1.0], 2, 2.0, 3),
        ([-2.0, -2.0, -3.0], 2, 2.0, 2),
        ([4.0, 4.0, 3.0], 2, 0.5, 2),
        ([1.0, 1.0, 3.0], 1, 2.0, 2),
        ([1.0, 1.0, 2.0 + 1e-8], 2, 2.0, 2),
        ([0.0, 0.0, 2e-12], 2, 2.0, 2),
        ([-1.0, -1.0, -2.0 + 1e-8], 2, 2.0, 2),
        ([1.0, 1.0, 1.0], 2, 2.0, None),
        ([9.0, 9.0], 2, 2.0, None),
        ([9.0], 3, 2.0, None),
        ([], 1, 2.0, None),
    ],
)
def test_e3_previous_window(
    values: list[float], window: int, factor: float, expected: int | None
) -> None:
    got = first_spike(values, window, factor)
    assert got == expected, (
        f"for {values}, window={window}, factor={factor}, expected first spike {expected}, got {got}"
    )


@pytest.mark.parametrize(
    "values",
    [
        [2.0, 2.0, 4.0],
        [0.0, 0.0, 0.0],
        [0.1, 0.4, 0.1, 0.1, 0.2],
        [1.0, 1.0, 2.0 + 1e-10],
        [0.0, 0.0, 5e-13],
        [-1.0, -1.0, -2.0 + 1e-10],
    ],
)
def test_e3_equal_threshold_is_not_spike(values: list[float]) -> None:
    assert first_spike(values, 2, 2.0) is None, "only a strict increase above the threshold counts"


@pytest.mark.parametrize("window", [0, -1])
@pytest.mark.parametrize("values", [[], [1.0, 2.0, 3.0]])
def test_e3_invalid_window(values: list[float], window: int) -> None:
    with pytest.raises(ValueError):
        first_spike(values, window, 2.0)


@pytest.mark.parametrize("factor", [0.0, -0.5, -3.0])
@pytest.mark.parametrize("values", [[], [1.0, 2.0, 3.0]])
def test_e3_invalid_factor(values: list[float], factor: float) -> None:
    with pytest.raises(ValueError):
        first_spike(values, 2, factor)


def test_e3_preserves_input() -> None:
    values = [2.0, 2.0, 5.0, 100.0]
    before = values.copy()
    assert first_spike(values, 2, 2.0) == 2
    assert values == before, "spike detection must not consume or rearrange the trace"


def test_e3_linear_sample_work() -> None:
    values = _ReadBudget([1.0] * 5999 + [10.0])
    assert first_spike(values, 300, 2.0) == 5999, "check every candidate using an updated baseline"


@pytest.mark.parametrize(
    "serials,expected",
    [
        (["PSU-7", "DMM-2", "PSU-7", "PSU-8"], ["PSU-7", "DMM-2", "PSU-8"]),
        (["Z-9", "A-1", "Z-9", "M-2", "A-1"], ["Z-9", "A-1", "M-2"]),
        (["PSU-7", "psu-7", " PSU-7 ", "PSU-7"], ["PSU-7", "psu-7", " PSU-7 "]),
        (["", "DMM-1", "", "DMM-1"], ["", "DMM-1"]),
        (["DMM-1"] * 4, ["DMM-1"]),
        (["DMM-1"], ["DMM-1"]),
        ([], []),
    ],
)
def test_e4_first_occurrences(serials: list[str], expected: list[str]) -> None:
    got = dedupe_keep_order(serials)
    assert got == expected, f"keep the first occurrence of each exact serial in {serials!r}"


def test_e4_preserves_input() -> None:
    serials = ["PSU-3", "DMM-1", "PSU-3"]
    before = serials.copy()
    got = dedupe_keep_order(serials)
    assert serials == before, "keep the original discovery log unchanged"
    assert got is not serials, "return a new list"


def test_e4_fast_enough() -> None:
    unique = [f"DMM-{index:06d}" for index in range(100_000)]
    serials = unique + unique[::-1]
    start = perf_counter()
    got = dedupe_keep_order(serials)
    elapsed = perf_counter() - start
    assert got == unique, "all 100,000 serials must appear once in discovery order"
    assert elapsed <= 2.0, f"dedupe_keep_order took {elapsed:.3f}s; use set membership (limit 2s)"
