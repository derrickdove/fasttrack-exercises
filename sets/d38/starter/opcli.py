"""Operator CLI exercises; the simulated backend and parser error adapter are supplied."""
from __future__ import annotations

import argparse
from collections.abc import Callable
import json
import math
from pathlib import Path
import sys
from typing import NoReturn


# Supplied station readings, in volts. None means that the instrument is offline.
STATIONS: dict[str, float | None] = {
    "bench-A": 5.0,
    "bench-B": 4.0,
    "bench-offline": None,
}


class _OperatorParser(argparse.ArgumentParser):
    """Supplied: let main format usage errors without argparse printing two lines."""

    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _run_station(limits_path: str, station: str, dry_run: bool) -> str:
    """Supplied: validate a JSON limits file, then check one simulated voltage."""
    data: object = json.loads(Path(limits_path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"low", "high"}:
        raise ValueError("limits must contain exactly low and high")
    low, high = data["low"], data["high"]
    if (
        isinstance(low, bool) or isinstance(high, bool)
        or not isinstance(low, (int, float)) or not isinstance(high, (int, float))
        or (isinstance(low, float) and not math.isfinite(low))
        or (isinstance(high, float) and not math.isfinite(high))
        or low > high
    ):
        raise ValueError("limits need finite numeric low <= high")
    if dry_run:
        return "READY"
    value = STATIONS[station]
    if value is None:
        return "ERROR"
    return "PASS" if low <= value <= high else "FAIL"


def build_parser() -> argparse.ArgumentParser:
    """E1: Build the station parser with required run/list/show subcommands."""
    raise NotImplementedError("E1: Use _OperatorParser and add the three subcommands")


def main(argv: list[str] | None = None) -> int:
    """E2: Dispatch operator commands; return 0/1/2/3 with clear one-line errors."""
    raise NotImplementedError("E2: Parse argv, dispatch, and translate outcomes to exit codes")


def format_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    """E3: Return a left-aligned header and rows, separated by two spaces."""
    raise NotImplementedError("E3: Calculate column widths and align station cells")


def confirm(prompt: str, input_fn: Callable[[str], str] = input) -> bool:
    """E4: Ask once; accept y/yes after stripping and lowercasing; EOF is False."""
    raise NotImplementedError("E4: Accept only an explicit yes and handle EOF safely")


if __name__ == "__main__":
    raise SystemExit(main())
