"""Read and check deployment files without starting a Linux service."""
from pathlib import Path
import tomllib
from typing import Any


def parse_unit(path: str | Path) -> dict[str, dict[str, list[str]]]:
    """Read the documented unit subset, preserving repeated assignments in order."""
    raise NotImplementedError("E2: Collect each section's keys into lists of values")


def validate_unit(parsed: dict[str, dict[str, list[str]]]) -> list[str]:
    """Return the ordered station service checklist problems from README.md."""
    raise NotImplementedError("E3: Check required service settings without changing parsed")


def load_station_toml(path: str | Path) -> dict[str, Any]:
    """Load TOML and validate station.name and the instrument table list."""
    raise NotImplementedError("E4: Load TOML and name the first missing or mistyped key")
