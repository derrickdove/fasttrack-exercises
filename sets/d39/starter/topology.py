"""Station configuration, setup dependencies, and scheduled instrument use."""
import heapq
from pathlib import Path
import tomllib
from typing import Any


# Supplied station wiring for E4. A UUT is a unit under test.
# Each PSU id identifies one independently controlled power-supply channel.
UUT_INSTRUMENTS: dict[str, tuple[str, ...]] = {
    "uut-a": ("psu-a", "dmm"),
    "uut-b": ("psu-b", "dmm"),
    "uut-c": ("scope",),
    "uut-d": ("dmm", "scope"),
}


def load(path: str | Path) -> dict[str, Any]:
    """Read TOML in binary mode; propagate file and TOML decoding errors."""
    raise NotImplementedError("E1: Read the station file with tomllib.load")


def validate(cfg: dict[str, Any]) -> list[str]:
    """Return sorted, unique configuration errors using the README messages."""
    raise NotImplementedError("E1: Check ids, resources, references, and PSU ownership")


def instruments_for(cfg: dict[str, Any], uut_id: str) -> list[str]:
    """Return sorted, unique instrument ids for a UUT; raise KeyError if absent."""
    raise NotImplementedError("E2: Find the UUT and return its instrument ids")


def setup_order(deps: dict[str, list[str]]) -> list[str]:
    """Use Kahn's algorithm, choosing the alphabetically first ready instrument."""
    raise NotImplementedError("E3: Order prerequisites before dependents or name a cycle")


def conflicts(schedule: list[tuple[str, int, int]]) -> list[tuple[str, str]]:
    """Sweep half-open windows using UUT_INSTRUMENTS; return sorted unique pairs."""
    raise NotImplementedError("E4: Sort windows and detect overlapping shared instruments")
