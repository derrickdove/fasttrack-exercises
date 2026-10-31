"""Model measurement outcomes and per-channel statistics for a test station."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto
from math import isfinite


class Status(Enum):
    """Named outcomes; enum values do not define severity order."""

    PASS = auto()
    FAIL = auto()
    ERROR = auto()


def worst(statuses: Iterable[Status]) -> Status:
    """Return ERROR above FAIL above PASS; return ERROR for no outcomes."""
    raise NotImplementedError("E1: Choose the most severe outcome, including empty input")


@dataclass(frozen=True)
class Reading:
    """One immutable channel measurement; only channel and value are validated."""

    channel: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        """Reject an empty channel or non-finite value with ValueError."""
        raise NotImplementedError("E2: Validate the channel and finite measurement value")

    def to_unit(self, unit: str) -> "Reading":
        """Return a new reading in V/mV or A/mA; reject other conversions."""
        raise NotImplementedError("E2: Convert within one supported unit family")


class RunningStats:
    """Incremental statistics for finite numbers, with constant work per add.

    Initialization and properties are supplied; E3 implements add.
    """

    def __init__(self) -> None:
        """Start an empty collection without retaining individual samples."""
        self._count = 0
        self._total = 0.0
        self._min: float | None = None
        self._max: float | None = None

    def add(self, value: float) -> None:
        """Include one finite number in the accumulated statistics."""
        raise NotImplementedError("E3: Update statistics without rescanning samples")

    @property
    def count(self) -> int:
        """Return the number of samples, initially zero."""
        return self._count

    @property
    def mean(self) -> float:
        """Return the arithmetic mean, or raise ValueError when empty."""
        if self._count == 0:
            raise ValueError("no samples")
        return self._total / self._count

    @property
    def min(self) -> float:
        """Return the smallest sample, or raise ValueError when empty."""
        if self._min is None:
            raise ValueError("no samples")
        return self._min

    @property
    def max(self) -> float:
        """Return the largest sample, or raise ValueError when empty."""
        if self._max is None:
            raise ValueError("no samples")
        return self._max


class ChannelBank:
    """Own one RunningStats per channel and require one unit per channel."""

    def __init__(self) -> None:
        """Start without channels."""
        raise NotImplementedError("E4: Initialize independent channel storage")

    def add(self, reading: Reading) -> None:
        """Accumulate a reading; reject a changed unit before changing state."""
        raise NotImplementedError("E4: Find or create the channel's RunningStats")

    def summary(self) -> dict[str, dict[str, int | float | str]]:
        """Return fresh nested dictionaries of unit, count, mean, min, and max."""
        raise NotImplementedError("E4: Build a detached summary for every channel")

    def __len__(self) -> int:
        """Return the number of distinct channels."""
        raise NotImplementedError("E4: Count channels rather than readings")
