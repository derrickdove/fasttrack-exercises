"""Gate-only helpers; learner modules load when a check runs, not at collection."""

from collections.abc import Callable
from importlib import import_module
from pathlib import Path
import re
from types import ModuleType

import pytest


@pytest.fixture
def models() -> ModuleType:
    return import_module("chassis.models")


@pytest.fixture
def limits() -> ModuleType:
    return import_module("chassis.limits")


@pytest.fixture
def csv_file(tmp_path: Path) -> Callable[[str], Path]:
    def write_csv(content: str) -> Path:
        path = tmp_path / "station limits.csv"
        path.write_text(content, encoding="utf-8")
        return path

    return write_csv


@pytest.fixture
def bad_limits(
    limits: ModuleType, csv_file: Callable[[str], Path]
) -> Callable[[str, int], None]:
    def assert_bad_file(content: str, line_number: int) -> None:
        with pytest.raises(limits.LimitFileError) as caught:
            limits.load_limits(csv_file(content))
        message = str(caught.value)
        assert re.search(rf"(?<!\d){line_number}(?!\d)", message), (
            f"expected physical file line {line_number} in error message, got {message!r}"
        )

    return assert_bad_file
