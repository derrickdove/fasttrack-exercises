"""Track the sequence numbers in a chassis test station's telemetry."""
from bisect import bisect_left
from collections import deque
from collections.abc import Callable


def seq_diff(a: int, b: int) -> int:
    """Return a minus b on a 16-bit ring; reject values outside 0..65535."""
    raise NotImplementedError("E1: Compute the signed difference on a 16-bit ring")


def missing_between(last: int, new: int) -> list[int]:
    """List skipped numbers for a forward step; otherwise return an empty list."""
    raise NotImplementedError("E2: List a forward gap, including wraparound")


class GapTracker:
    """Track arrivals, recent duplicates, late packets and still-missing numbers."""

    received: int
    duplicates: int
    out_of_order: int
    missing: set[int]

    def __init__(self) -> None:
        """Start empty with a duplicate window of 1024 arrivals."""
        raise NotImplementedError("E3: Initialize counters, missing set and recent history")

    def update(self, seq: int) -> list[int]:
        """Process one arrival using the rules in the README; return its new gap."""
        raise NotImplementedError("E3: Classify this arrival and update the tracker")


def loss_report(seqs: list[int]) -> dict[str, int | float]:
    """Return received, missing, loss_pct and longest_gap as defined in the README."""
    raise NotImplementedError("E4: Summarize one stream using a fresh GapTracker")


class EventCounter:
    """Count dropped-packet events in an inclusive millisecond window."""

    def __init__(self, clock: Callable[[], int]) -> None:
        """Accept a clock returning integer milliseconds that never go backwards."""
        raise NotImplementedError("E5: Store the clock and initialize bounded event history")

    def record(self) -> None:
        """Record one event at the current time and discard expired events."""
        raise NotImplementedError("E5: Record one event, keeping at most 10,000 ms of history")

    def count_last(self, ms: int) -> int:
        """Count events in [now - ms, now]; reject non-int or out-of-range ms."""
        raise NotImplementedError("E5: Validate the window and count its events efficiently")

    def __len__(self) -> int:
        """Discard expired events and return the number of stored events."""
        raise NotImplementedError("E5: Return the size of the retained event history")
