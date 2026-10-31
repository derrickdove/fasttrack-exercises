"""Station event logs and pytest JUnit reports."""
from collections import Counter, defaultdict
import logging
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


def get_station_logger(name: str, path: str | Path) -> logging.Logger:
    """Append INFO+ events to a UTF-8 file without adding duplicate handlers."""
    raise NotImplementedError("E1: configure a named logger with one file handler")


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Count observed statuses and return the worst: ERROR, FAIL, then PASS."""
    raise NotImplementedError("E2: count statuses with Counter and choose the worst")


def failures_by_channel(results: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group FAIL and ERROR messages by channel, keeping their input order."""
    raise NotImplementedError("E3: collect failure messages with defaultdict(list)")


def read_junit(path: str | Path) -> list[dict[str, Any]]:
    """Read test names, outcomes and per-test properties in XML document order."""
    raise NotImplementedError("E4: read each JUnit testcase outcome and its properties")
