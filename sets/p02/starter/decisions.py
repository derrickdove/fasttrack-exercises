"""Small decisions and loops for test-station readings."""


def is_over_limit(reading: float, limit: float) -> bool:
    """Return whether a reading is strictly greater than its limit."""
    raise NotImplementedError("E1: Return whether the reading is over the limit")


def pass_or_fail(reading: float, limit: float) -> str:
    """Return FAIL above the limit and PASS otherwise."""
    raise NotImplementedError("E2: Choose PASS or FAIL with if and else")


def reading_band(reading: float, low: float, high: float) -> str:
    """Return LOW, OK, or HIGH; equality with either limit is OK."""
    raise NotImplementedError("E3: Classify the reading with if, elif, and else")


def is_in_range(reading: float, low: float, high: float) -> bool:
    """Return whether a reading is inside both inclusive limits."""
    raise NotImplementedError("E4: Join the two limit comparisons with and")


def total_readings(readings: list[float]) -> float:
    """Return the sum of the readings, or 0.0 for an empty list."""
    raise NotImplementedError("E5: Add each reading to a running total")


def count_over_limit(readings: list[float], limit: float) -> int:
    """Count readings strictly greater than the limit."""
    raise NotImplementedError("E6: Count readings over the limit with a for loop")


def first_over_limit(readings: list[float], limit: float) -> float | None:
    """Return the first reading over the limit, or None if none fail."""
    raise NotImplementedError("E7: Return the first failing value or None")


def channel_numbers(n: int) -> list[int]:
    """Return channel numbers from 1 through n; n is zero or greater."""
    raise NotImplementedError("E8: Build a channel list with range and append")


def steps_to_target(target: float, step: float) -> int:
    """Count positive steps from zero until reaching or exceeding the target."""
    raise NotImplementedError("E9: Count voltage steps with a while loop")


def checked_channel_numbers(count: int) -> list[int]:
    """Reject a negative count, otherwise return its channel numbers."""
    raise NotImplementedError("E10: Guard against a negative count with ValueError")


def bug_answers() -> dict[str, str]:
    """Map Q1 through Q3 to uppercase option letters from the README."""
    raise NotImplementedError("E11: Choose one option for each bug question")
