"""Measure station-step latency and choose where optimization belongs."""

from collections.abc import Callable
import math
import statistics
import time


def measure(
    fn: Callable[[], object], runs: int, clock: Callable[[], float] = time.perf_counter
) -> dict[str, float]:
    """E5: Time each call and return min, median, nearest-rank p99, and max in ms."""
    raise NotImplementedError("E5: time each call and summarize the durations in milliseconds")


def meets_deadline(stats: dict[str, float], deadline_ms: float) -> bool:
    """E5: Decide whether every measured call finished within the deadline."""
    raise NotImplementedError("E5: compare the maximum duration with the deadline")


def speed_answers() -> dict[str, str]:
    """E6: Return option letters for Q1, Q2, and Q3 from the README."""
    raise NotImplementedError("E6: choose evidence-based language and optimization decisions")
