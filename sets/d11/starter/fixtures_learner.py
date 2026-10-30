"""Implement the four fixtures used by this station's tests."""
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TypedDict

import pytest

from starter.fakes import FakeInstrument


class Reading(TypedDict):
    """One named measurement, its numeric value, and its unit."""

    name: str
    value: float
    unit: str


@pytest.fixture
def fake_psu() -> FakeInstrument:
    """E1: Return a fresh scripted power supply for each test."""
    raise NotImplementedError("E1: return a fresh FakeInstrument with the specified replies")


@pytest.fixture
def limits_file(tmp_path: Path) -> Path:
    """E2: Write limits.csv inside tmp_path and return its Path."""
    raise NotImplementedError("E2: write the specified limits CSV in tmp_path")


@pytest.fixture
def powered_psu(fake_psu: FakeInstrument) -> Iterator[FakeInstrument]:
    """E3: Enable output, yield this supply, and always disable output."""
    raise NotImplementedError("E3: use yield and finally to turn the output off")


@pytest.fixture
def make_reading() -> Callable[..., Reading]:
    """E4: Return a function building independent Reading dictionaries."""
    raise NotImplementedError("E4: return a reading factory with the specified defaults")
