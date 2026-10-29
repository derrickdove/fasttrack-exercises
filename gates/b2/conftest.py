"""Load learner modules at check time so an empty package still collects tests."""

from importlib import import_module
from types import ModuleType

import pytest


@pytest.fixture
def models() -> ModuleType:
    return import_module("chassis.models")


@pytest.fixture
def themis() -> ModuleType:
    return import_module("chassis.themis")


@pytest.fixture
def report() -> ModuleType:
    return import_module("chassis.report")


@pytest.fixture
def mixed_results(models: ModuleType, themis: ModuleType) -> list:
    return [
        themis.CheckResult("bus_voltage", 24.0, 22.0, 30.0, "V", models.Status.PASS, "within limits"),
        themis.CheckResult("supply_current", 4.0, None, 3.0, "A", models.Status.FAIL, "above high bound 3.0"),
        themis.CheckResult("temperature", None, -20.0, None, "degC", models.Status.ERROR, "not measured"),
    ]
