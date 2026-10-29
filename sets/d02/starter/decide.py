"""Decisions for voltage readings at a test station."""


def classify(value: float, low: float | None, high: float | None) -> str:
    """Return LOW, HIGH, or PASS; equality passes and None removes a limit."""
    raise NotImplementedError("E1: Compare a reading with each supplied limit.")


def count_failures(values: list[float], low: float, high: float) -> int:
    """Count readings outside inclusive limits; an empty list returns 0."""
    raise NotImplementedError("E2: Count each reading outside the limits.")


def first_out_of_limits(
    values: list[float], low: float, high: float
) -> int | None:
    """Return the first failing zero-based index, or None if none fail."""
    raise NotImplementedError("E3: Return the index of the first failing reading.")


def settle_index(
    values: list[float], target: float, tolerance: float, hold: int
) -> int | None:
    """Return the first run's start, or None; tolerance >= 0 and hold >= 1."""
    raise NotImplementedError("E4: Find hold consecutive readings within tolerance.")
