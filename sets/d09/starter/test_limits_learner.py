"""Replace each unfinished body with assertions about the supplied station checker."""
import pytest

from starter.limits_lib import classify


def test_e1_inclusive_bounds() -> None:
    """Check below, inside, above, both endpoints, and an equal-limit window."""
    raise NotImplementedError("E1: assert the status for ordinary and boundary readings")


def test_e2_missing_reading() -> None:
    """Check None with two different valid limit windows."""
    raise NotImplementedError("E2: assert that an absent reading is MISSING")


def test_e3_nan_reading() -> None:
    """Check float('nan') with two different valid limit windows."""
    raise NotImplementedError("E3: assert that a NaN reading is INVALID")


def test_e4_reversed_limits() -> None:
    """Check that reversed limits raise before classifying any kind of reading."""
    raise NotImplementedError("E4: use pytest.raises for reversed limits")
