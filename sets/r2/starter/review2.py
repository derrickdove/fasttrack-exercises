"""Week 2 station review. Implement E1-E3 and E6-E7; leave supplied E4-E5 helpers alone."""
from collections import Counter, deque
from collections.abc import Callable, Iterable
import csv
import logging
import math
from pathlib import Path


def current_in_amps(value: float, unit: str) -> float:
    """E1: Convert A, mA or uA into amperes; reject unknown units."""
    raise NotImplementedError("E1: convert the current using the exact unit")


def summarize(statuses: list[str]) -> tuple[dict[str, int], str]:
    """E2: Return all three status counts and the worst status, or NOT_RUN."""
    raise NotImplementedError("E2: count statuses and choose the worst result")


def rolling_bad_counts(statuses: Iterable[str], window: int) -> list[int]:
    """E3: Count FAIL and ERROR in each full window with one pass and a deque."""
    raise NotImplementedError("E3: keep a bounded window and a running bad count")


# Supplied helpers for E4 and E5. Do not change these functions.
def current_status(value: float, low: float, high: float) -> str:
    """Classify amperes against inclusive limits; invalid numbers raise ValueError."""
    if not all(math.isfinite(number) for number in (value, low, high)):
        raise ValueError("current and limits must be finite")
    if low > high:
        raise ValueError("low must not exceed high")
    if value < low:
        return "LOW"
    if value > high:
        return "HIGH"
    return "PASS"


def log_status(logger: logging.Logger, channel: str, status: str) -> None:
    """Emit exactly one record: WARNING for FAIL, INFO for PASS."""
    level = logging.WARNING if status == "FAIL" else logging.INFO
    logger.log(level, "%s: %s", channel, status)


# Earlier-week retention exercises.
def load_limit_bands(path: str | Path) -> dict[str, tuple[float, float]]:
    """E6: Read channel,low,high CSV; reject reversed limits; later rows win."""
    raise NotImplementedError("E6: read CSV rows and store each channel's numeric limits")


def station_readiness(query: Callable[[str], str]) -> str:
    """E7: Query STAT:READY? once; map 1/0 to READY/BUSY, timeout to OFFLINE."""
    raise NotImplementedError("E7: catch only TimeoutError and validate the stripped reply")
