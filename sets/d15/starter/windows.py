"""Fast summaries of ordered test-station sensor readings."""
from collections import deque


def rolling_mean(values: list[float], window: int) -> list[float]:
    """E1: Return the mean of each full window; reject window <= 0."""
    raise NotImplementedError("E1: Slide a running sum across the readings")


def max_in_windows(values: list[float], window: int) -> list[float]:
    """E2: Return each full window's maximum using a monotonic deque."""
    raise NotImplementedError("E2: Keep candidate indices in a deque")


def first_spike(values: list[float], window: int, factor: float) -> int | None:
    """E3: Find the first reading above factor times its preceding mean."""
    raise NotImplementedError("E3: Compare before updating the previous-window sum")


def dedupe_keep_order(serials: list[str]) -> list[str]:
    """E4: Keep the first occurrence of each exact serial string in O(n)."""
    raise NotImplementedError("E4: Track seen serials with a set")
