"""Station event logs and JSON run reports."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any


def get_station_logger(name: str, path: str | Path) -> logging.Logger:
    """Append INFO+ events to a UTF-8 file without adding duplicate handlers."""
    raise NotImplementedError("E1: configure a named logger with one file handler")


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Count observed statuses and return the worst: ERROR, FAIL, then PASS."""
    raise NotImplementedError("E2: count statuses with Counter and choose the worst")


def failures_by_channel(results: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group FAIL and ERROR messages by channel, keeping their input order."""
    raise NotImplementedError("E3: collect failure messages with defaultdict(list)")


def write_report(
    results: list[dict[str, Any]],
    path: str | Path,
    meta: dict[str, Any],
    *,
    now: datetime | None = None,
) -> None:
    """Write meta (including generated_utc), summary and results as UTF-8 JSON."""
    raise NotImplementedError("E4: copy metadata, add UTC time, and write the report")
