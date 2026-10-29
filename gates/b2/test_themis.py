"""Block 2's public result records and checking rules."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
import math
from types import ModuleType

import pytest


def test_check_result_is_dataclass_with_contract_fields(models: ModuleType, themis: ModuleType) -> None:
    result = themis.CheckResult(
        name="bus_voltage", value=24.0, low=22.0, high=30.0,
        unit="V", status=models.Status.PASS, message="within limits",
    )
    assert is_dataclass(result)
    assert [field.name for field in fields(result)] == [
        "name", "value", "low", "high", "unit", "status", "message"
    ]
    assert result == themis.CheckResult("bus_voltage", 24.0, 22.0, 30.0, "V", models.Status.PASS, "within limits")


def test_check_result_fields_are_frozen(models: ModuleType, themis: ModuleType) -> None:
    result = themis.CheckResult("bus_voltage", 24.0, 22.0, 30.0, "V", models.Status.PASS, "ok")
    replacements = {
        "name": "rail", "value": None, "low": None, "high": None,
        "unit": "mV", "status": models.Status.FAIL, "message": "changed",
    }
    for field, value in replacements.items():
        with pytest.raises(FrozenInstanceError):
            setattr(result, field, value)


@pytest.mark.parametrize("value,low,high", [
    (24.0, 22.0, 30.0), (22.0, 22.0, 30.0), (30.0, 22.0, 30.0),
    (5.0, 5.0, 5.0), (50.0, 0.0, None), (-50.0, None, 0.0), (0.0, 0.0, 0.0),
], ids=["inside", "at-low", "at-high", "equal-bounds", "low-only", "high-only", "at-zero"])
def test_check_passes_inside_inclusive_bounds(
    models: ModuleType, themis: ModuleType,
    value: float, low: float | None, high: float | None,
) -> None:
    result = themis.check(models.Measurement("bus_voltage", value, "V"), models.Limit("bus_voltage", low, high, "V"))
    assert isinstance(result, themis.CheckResult)
    assert (result.name, result.value, result.low, result.high, result.unit) == (
        "bus_voltage", value, low, high, "V"
    )
    assert result.status == models.Status.PASS


@pytest.mark.parametrize("value,low,high,bound_words", [
    (21.9, 22.0, 30.0, ("low", "below", "minimum")),
    (30.1, 22.0, 30.0, ("high", "above", "maximum", "upper")),
    (-0.1, 0.0, None, ("low", "below", "minimum")),
    (0.1, None, 0.0, ("high", "above", "maximum", "upper")),
], ids=["below-low", "above-high", "below-zero-low", "above-zero-high"])
def test_check_fails_outside_bounds_and_names_the_bound(
    models: ModuleType, themis: ModuleType, value: float,
    low: float | None, high: float | None, bound_words: tuple[str, ...],
) -> None:
    result = themis.check(models.Measurement("bus_voltage", value, "V"), models.Limit("bus_voltage", low, high, "V"))
    assert result.status == models.Status.FAIL
    assert result.value == value
    assert (result.low, result.high) == (low, high)
    assert any(word in result.message.casefold() for word in bound_words), result.message


def test_check_unit_mismatch_is_error_with_unit_message(models: ModuleType, themis: ModuleType) -> None:
    result = themis.check(models.Measurement("bus_voltage", 24.0, "mV"), models.Limit("bus_voltage", 22.0, 30.0, "V"))
    assert result.status == models.Status.ERROR
    assert "unit" in result.message.casefold()


def test_check_nan_is_error(models: ModuleType, themis: ModuleType) -> None:
    result = themis.check(models.Measurement("bus_voltage", math.nan, "V"), models.Limit("bus_voltage", 22.0, 30.0, "V"))
    assert result.status == models.Status.ERROR


def test_check_all_sorts_limits_then_unexpected_names(models: ModuleType, themis: ModuleType) -> None:
    limits = {name: models.Limit(name, 0.0, 30.0, "V") for name in ["z_rail", "b_rail"]}
    readings = [models.Measurement(name, 24.0, "V") for name in ["y_extra", "z_rail", "a_extra", "b_rail"]]
    results = themis.check_all(readings, limits)
    assert isinstance(results, list)
    assert [result.name for result in results] == ["b_rail", "z_rail", "a_extra", "y_extra"]
    for result in results[:2]:
        assert result == themis.check(models.Measurement(result.name, 24.0, "V"), limits[result.name])


def test_check_all_missing_measurement_has_none_value_and_error(models: ModuleType, themis: ModuleType) -> None:
    limits = {"bus_voltage": models.Limit("bus_voltage", 22.0, 30.0, "V")}
    results = themis.check_all([], limits)
    assert len(results) == 1
    result = results[0]
    assert result.name == "bus_voltage"
    assert result.value is None
    assert result.status == models.Status.ERROR
    assert "not measured" in result.message.casefold()


def test_check_all_unexpected_measurement_has_no_bounds(models: ModuleType, themis: ModuleType) -> None:
    results = themis.check_all([models.Measurement("supply_current", 1.5, "A")], {})
    assert len(results) == 1
    result = results[0]
    assert (result.name, result.value, result.low, result.high, result.unit) == (
        "supply_current", 1.5, None, None, "A"
    )
    assert result.status == models.Status.ERROR
    assert "no limit" in result.message.casefold()


@pytest.mark.parametrize("has_limit", [True, False], ids=["with-limit", "without-limit"])
def test_check_all_duplicate_measurement_is_error(
    models: ModuleType, themis: ModuleType, has_limit: bool,
) -> None:
    limits = {"bus_voltage": models.Limit("bus_voltage", 22.0, 30.0, "V")} if has_limit else {}
    readings = [models.Measurement("bus_voltage", 24.0, "V")] * 3
    readings.insert(1, models.Measurement("supply_current", 1.0, "A"))
    results = themis.check_all(readings, limits)
    duplicate_results = [result for result in results if result.name == "bus_voltage"]
    assert duplicate_results, "a duplicated name must still produce a result"
    assert all(result.status == models.Status.ERROR for result in duplicate_results)
    assert any("duplicate measurement" in result.message.casefold() for result in duplicate_results)
    assert any(result.name == "supply_current" for result in results)


def test_check_all_empty_inputs_return_empty_list(themis: ModuleType) -> None:
    assert themis.check_all([], {}) == []


def test_check_all_accepts_one_shot_measurement_iterator(models: ModuleType, themis: ModuleType) -> None:
    limit = models.Limit("bus_voltage", 22.0, 30.0, "V")
    reading = models.Measurement("bus_voltage", 31.0, "V")
    assert themis.check_all(iter([reading]), {limit.name: limit}) == [themis.check(reading, limit)]


@pytest.mark.parametrize("statuses,expected", [
    (["PASS", "PASS"], "PASS"), (["FAIL"], "FAIL"), (["ERROR"], "ERROR"),
    (["PASS", "FAIL", "PASS"], "FAIL"), (["FAIL", "ERROR", "PASS"], "ERROR"), (["ERROR", "FAIL"], "ERROR"),
], ids=["all-pass", "fail-only", "error-only", "fail-over-pass", "error-over-fail", "error-before-fail"])
def test_overall_uses_error_then_fail_then_pass(
    models: ModuleType, themis: ModuleType, statuses: list[str], expected: str,
) -> None:
    results = [themis.CheckResult("bus_voltage", 24.0, 22.0, 30.0, "V", models.Status(status), "reading") for status in statuses]
    assert themis.overall(results) == models.Status(expected)


def test_overall_empty_input_is_error(models: ModuleType, themis: ModuleType) -> None:
    assert themis.overall([]) == models.Status.ERROR


def test_overall_accepts_one_shot_result_iterator(models: ModuleType, themis: ModuleType, mixed_results: list) -> None:
    assert themis.overall(iter(mixed_results)) == models.Status.ERROR
