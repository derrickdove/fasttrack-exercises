"""Numerical acceptance checks shared by all station instruments.

A limits band has a lower and upper bound in the measurement's own unit.
Invalid configuration or a nonfinite measurement is an error, not a pass.
Keep that distinction: the runner records errors separately from failures.
"""

import math


def validate_limits(low: float, high: float) -> None:
    """Reject reversed bounds, infinity, or NaN before a step starts."""
    if not math.isfinite(low) or not math.isfinite(high) or low > high:
        raise ValueError("limits must be finite and ordered")


def check_limits(value: float, low: float, high: float) -> bool:
    """Compare a finite measurement with the configured acceptance band.

    Units are already consistent at the call site. No rounding, conversion,
    or instrument communication belongs in this shared numeric helper.
    """
    validate_limits(low, high)
    if not math.isfinite(value):
        raise ValueError("measurement must be finite")
    return low < value < high
