"""Review fixes for a station's voltage limit checker."""
import re


def within_limits(value: float, low: float, high: float) -> bool:
    """E1: Accept finite values inside inclusive, finite, ordered bounds.

    Supplied buggy body for review (copy it out, then fix it):
        return low < value < high
    """
    raise NotImplementedError("E1: fix the inclusive boundary comparison")


def failed_channels(readings: dict[str, float], low: float, high: float) -> list[str]:
    """E2: Return every failing channel name, sorted, without changing readings.

    Supplied buggy body for review (copy it out, then fix it):
        failures = []
        for channel in sorted(readings):
            if not within_limits(readings[channel], low, high):
                failures.append(channel)
            return failures
        return failures
    """
    raise NotImplementedError("E2: check every channel before returning")


def branch_name_ok(name: str) -> bool:
    """E4: Match feature/CTS-<digits>-<slug> or fix/CTS-<digits>-<slug>."""
    raise NotImplementedError("E4: validate the entire station-work branch name")

