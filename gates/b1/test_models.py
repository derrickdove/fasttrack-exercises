"""Block 1's public measurement and limit records."""

from dataclasses import FrozenInstanceError, is_dataclass
from enum import Enum
from types import ModuleType

import pytest


def test_status_is_enum_with_three_named_values(models: ModuleType) -> None:
    assert issubclass(models.Status, Enum)
    assert {member.name: member.value for member in models.Status} == {
        "PASS": "PASS", "FAIL": "FAIL", "ERROR": "ERROR"
    }


def test_measurement_is_dataclass_with_named_fields(models: ModuleType) -> None:
    reading = models.Measurement(name="bus_voltage", value=24.1, unit="V")
    assert is_dataclass(reading), "Measurement must be a dataclass"
    assert (reading.name, reading.value, reading.unit) == ("bus_voltage", 24.1, "V")
    assert reading == models.Measurement("bus_voltage", 24.1, "V")


def test_measurement_fields_are_frozen(models: ModuleType) -> None:
    reading = models.Measurement("bus_voltage", 24.1, "V")
    for field, replacement in [("name", "rail"), ("value", 25.0), ("unit", "mV")]:
        with pytest.raises(FrozenInstanceError):
            setattr(reading, field, replacement)


def test_limit_is_dataclass_with_named_fields(models: ModuleType) -> None:
    limit = models.Limit(name="bus_voltage", low=22.0, high=30.0, unit="V")
    assert is_dataclass(limit), "Limit must be a dataclass"
    assert (limit.name, limit.low, limit.high, limit.unit) == (
        "bus_voltage", 22.0, 30.0, "V"
    )
    assert limit == models.Limit("bus_voltage", 22.0, 30.0, "V")


@pytest.mark.parametrize("low,high", [(0.0, None), (None, 0.0)], ids=["low-only", "high-only"])
def test_limit_accepts_one_bound_including_zero(
    models: ModuleType, low: float | None, high: float | None
) -> None:
    limit = models.Limit("offset", low, high, "V")
    assert (limit.low, limit.high) == (low, high)


def test_limit_accepts_equal_bounds(models: ModuleType) -> None:
    limit = models.Limit("reference_voltage", 5.0, 5.0, "V")
    assert (limit.low, limit.high) == (5.0, 5.0)


def test_limit_rejects_low_greater_than_high(models: ModuleType) -> None:
    with pytest.raises(ValueError):
        models.Limit("bus_voltage", 30.0, 22.0, "V")


def test_limit_rejects_two_missing_bounds(models: ModuleType) -> None:
    with pytest.raises(ValueError):
        models.Limit("bus_voltage", None, None, "V")


@pytest.mark.parametrize("low,high", [
    (float("nan"), None), (None, float("nan")),
    (float("nan"), 30.0), (22.0, float("nan")), (float("nan"), float("nan")),
], ids=["nan-low-only", "nan-high-only", "nan-low", "nan-high", "both-nan"])
def test_limit_rejects_nan_bounds(
    models: ModuleType, low: float | None, high: float | None,
) -> None:
    with pytest.raises(ValueError):
        models.Limit("rail", low, high, "V")


def test_limit_fields_are_frozen(models: ModuleType) -> None:
    limit = models.Limit("bus_voltage", 22.0, 30.0, "V")
    for field, replacement in [
        ("name", "rail"), ("low", 20.0), ("high", 31.0), ("unit", "mV")
    ]:
        with pytest.raises(FrozenInstanceError):
            setattr(limit, field, replacement)
