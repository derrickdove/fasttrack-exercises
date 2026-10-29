"""Supplied station limit checker. You write its tests, not this implementation."""
from math import isnan


def classify(value: float | None, low: float, high: float) -> str:
    """Classify a reading using finite inclusive limits; reject reversed limits first."""
    if low > high:
        raise ValueError("low must be less than or equal to high")
    if value is None:
        return "MISSING"
    if isnan(value):
        return "INVALID"
    if value < low:
        return "LOW"
    if value > high:
        return "HIGH"
    return "PASS"
