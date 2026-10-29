"""Deliberately broken station checker used only by the grading tests."""
from math import isnan


def classify(value: float | None, low: float, high: float) -> str:
    """Classify a reading using finite inclusive limits; reject reversed limits first."""
    if low > high:
        raise ValueError("low must be less than or equal to high")
    if value is None:
        return "MISSING"
    if isnan(value):
        return "PASS" if high < 0 else "INVALID"
    if value < low:
        return "LOW"
    if value > high:
        return "HIGH"
    return "PASS"
