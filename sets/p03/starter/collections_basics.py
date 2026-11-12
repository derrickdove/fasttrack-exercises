"""Practice small collection operations for a test station."""


def make_readings(first: float, second: float, third: float) -> list[float]:
    """Collect three readings in arrival order using append."""
    raise NotImplementedError("E1: Append three readings to a new list")


def last_reading(values: list[float]) -> float:
    """Return the last item of a nonempty reading list."""
    raise NotImplementedError("E2: Return the last reading using a negative index")


def reading_count(values: list[float]) -> int:
    """Return the number of readings, including zero for an empty list."""
    raise NotImplementedError("E2: Return the number of readings")


def readings_above(values: list[float], limit: float) -> list[float]:
    """Return readings strictly above the limit in their original order."""
    raise NotImplementedError("E3: Build a new list of readings above the limit")


def smallest_reading(values: list[float]) -> float:
    """Return the smallest reading from a nonempty list."""
    raise NotImplementedError("E4: Return the smallest reading")


def largest_reading(values: list[float]) -> float:
    """Return the largest reading from a nonempty list."""
    raise NotImplementedError("E4: Return the largest reading")


def total_readings(values: list[float]) -> float:
    """Return the sum of a nonempty list of readings."""
    raise NotImplementedError("E4: Return the total of the readings")


def average_reading(values: list[float]) -> float:
    """Return the unrounded average of a nonempty list of readings."""
    raise NotImplementedError("E5: Divide the readings' total by their count")


def lookup_status(statuses: dict[str, str], name: str) -> str:
    """Return a named channel's status or UNKNOWN if the key is absent."""
    raise NotImplementedError("E6: Check for the key before looking up its status")


def count_statuses(statuses: list[str]) -> dict[str, int]:
    """Return each status and how many times it appears."""
    raise NotImplementedError("E7: Count occurrences of each status in a dictionary")


def channels_over_limit(readings: dict[str, float], limit: float) -> list[str]:
    """Return names strictly over the limit in dictionary insertion order."""
    raise NotImplementedError("E8: Visit dictionary items and collect names over the limit")


def record_channels(records: list[dict[str, str]]) -> list[str]:
    """Return each record's channel field in record order."""
    raise NotImplementedError("E9: Collect the channel field from every record")


def ascending_readings(values: list[float]) -> list[float]:
    """Return a new ascending list of the nonempty input's readings."""
    raise NotImplementedError("E10: Return the readings in ascending order")


def sorted_channels(channels: list[int]) -> list[int]:
    """Return a new sorted channel list without changing the input."""
    raise NotImplementedError("E10: Return a sorted copy and keep the input unchanged")


def unique_channels(channels: list[int]) -> list[int]:
    """Return distinct channel numbers in a new ascending list."""
    raise NotImplementedError("E11: Remove repeated channel numbers and sort the result")


def collection_answers() -> dict[str, str]:
    """Return chosen option letters for collection questions Q1 through Q3."""
    raise NotImplementedError("E12: Choose fixes for the three collection mistakes")
