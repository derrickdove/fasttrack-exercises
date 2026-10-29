def group_by_channel(readings: list[tuple[str, float]]) -> dict[str, list[float]]:
    """Group readings by exact channel name, preserving each channel's value order."""
    raise NotImplementedError("E1: collect each channel's values in a list")


def channel_stats(
    readings: list[tuple[str, float]],
) -> dict[str, tuple[float, float, float]]:
    """Return (minimum, maximum, arithmetic mean) for each channel."""
    raise NotImplementedError("E2: calculate the three statistics for each channel")


def missing_channels(expected: list[str], seen: list[str]) -> list[str]:
    """Return sorted, unique expected channel names absent from seen."""
    raise NotImplementedError("E3: use fast membership checks to find missing channels")


def duplicate_serials(serials: list[str]) -> list[str]:
    """Return upper-case repeated serials in order of their second appearance."""
    raise NotImplementedError("E4: track seen serials and report each duplicate once")
