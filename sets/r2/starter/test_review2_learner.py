"""E4-E5: write pytest tests for the supplied helpers in review2.py."""
import logging

import pytest

from starter.review2 import current_status, log_status


# Supplied inputs keep the review short; you write the checks.
@pytest.mark.parametrize(
    "value,low,high,expected",
    [(0.5, 1.0, 2.0, "LOW"), (1.0, 1.0, 2.0, "PASS"),
     (1.5, 1.0, 2.0, "PASS"), (2.0, 1.0, 2.0, "PASS"),
     (2.5, 1.0, 2.0, "HIGH"), (-1.0, -1.0, -1.0, "PASS")],
)
def test_e4_current_status(value: float, low: float, high: float, expected: str) -> None:
    """Assert the supplied helper returns the expected status."""
    raise NotImplementedError("E4: compare current_status with expected")


def test_e4_reversed_limits() -> None:
    """Check current_status(1.5, 2.0, 1.0) raises ValueError."""
    raise NotImplementedError("E4: use pytest.raises for reversed limits")


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("number", [float("nan"), float("inf"), -float("inf")])
def test_e4_nonfinite(position: int, number: float) -> None:
    """Replace arguments[position] in [1.5, 1.0, 2.0]; expect ValueError."""
    raise NotImplementedError("E4: replace one argument and check rejection with pytest.raises")


@pytest.mark.parametrize("status,expected_level", [("PASS", logging.INFO), ("FAIL", logging.WARNING)])
def test_e5_status_logging(caplog: pytest.LogCaptureFixture, status: str, expected_level: int) -> None:
    """Capture records and test level, text and count for the supplied status."""
    raise NotImplementedError("E5: use caplog to check exactly one station log record")
