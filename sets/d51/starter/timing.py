"""Measure station-step latency and diagnose captured bench evidence."""

from collections.abc import Callable
import math
import statistics
import time


def summarize_durations(durations_ms: list[float]) -> dict[str, float]:
    """Supplied E5 helper: summarize a nonempty list of elapsed milliseconds.

    Values must be finite and nonnegative. Sorting a copy preserves the input.
    measure() owns collecting valid durations; leave this helper unchanged.
    """
    durations = sorted(durations_ms)
    return {
        "min": durations[0],
        "median": float(statistics.median(durations)),
        "p99": durations[math.ceil(0.99 * len(durations)) - 1],
        "max": durations[-1],
    }


def measure(
    fn: Callable[[], object], runs: int, clock: Callable[[], float] = time.perf_counter
) -> dict[str, float]:
    """E5 TODO: Collect per-call milliseconds; return summarize_durations(values)."""
    raise NotImplementedError("E5: collect per-call milliseconds and call the supplied summary helper")


def meets_deadline(stats: dict[str, float], deadline_ms: float) -> bool:
    """E5: Decide whether every measured call finished within the deadline."""
    raise NotImplementedError("E5: compare the maximum duration with the deadline")


def diagnose_captures() -> dict[str, dict[str, str]]:
    """E6 TODO: Diagnose case_a and case_b using data/ and the README contract.

    For each case return fault, serial_evidence, dmm_evidence, scope_evidence,
    next_measurement, and disposition. No file parser is required.
    """
    raise NotImplementedError("E6: weigh the serial, DMM, and scope evidence and choose the next measurement")
