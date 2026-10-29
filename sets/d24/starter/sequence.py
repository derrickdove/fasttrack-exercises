"""Track the sequence numbers in a chassis test station's telemetry."""
from collections import deque


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
