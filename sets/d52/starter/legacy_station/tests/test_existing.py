"""Existing checks: keep these passing while extending the station."""

import pytest

from starter.legacy_station.base import Driver
from starter.legacy_station.limits import check_limits
from starter.legacy_station.meter import VoltageMeter
from starter.legacy_station.runner import LAST_REPORT, Step, run_station
from starter.legacy_station.supply import PowerSupply
from starter.legacy_station.tests.fakes import FakeTransport


@pytest.mark.parametrize("kind", [VoltageMeter, PowerSupply])
def test_e2_existing_voltage_drivers(kind: type[Driver]) -> None:
    transport = FakeTransport({"MEAS:VOLT?": " 5.25\n", "*IDN?": "STATION,V1\n"})
    driver = kind(transport, timeout_s=0.75)
    assert driver.identify() == "STATION,V1", "strip the identification reply"
    assert driver.read() == 5.25, "the existing voltage drivers return volts"
    assert transport.queries == [("*IDN?", 0.75), ("MEAS:VOLT?", 0.75)]
    if isinstance(driver, PowerSupply):
        driver.set_voltage(12.5)
        driver.enable(True)
        driver.enable(False)
        assert transport.writes == [("VOLT 12.500", 0.75), ("OUTP ON", 0.75), ("OUTP OFF", 0.75)]
        with pytest.raises(ValueError):
            driver.set_voltage(31.0)
    if isinstance(driver, VoltageMeter):
        driver.zero()
        assert transport.writes == [("ZERO", 0.75)]


def test_e2_existing_runner_and_snapshot() -> None:
    transport = FakeTransport({"MEAS:VOLT?": "5"})
    drivers: dict[str, Driver] = {"meter": VoltageMeter(transport)}
    rows = run_station(drivers, [Step("rail", "meter", 4, 6, 2), Step("too_low", "meter", 6, 8)])
    assert [(row.name, row.value, row.status) for row in rows] == [
        ("rail", 5.0, "PASS"), ("too_low", 5.0, "FAIL")
    ], "keep report order and average the requested readings"
    assert LAST_REPORT == {"steps": 2, "passed": 1, "failed": 1, "errors": 0}
    assert len(transport.queries) == 3
    assert run_station(drivers, []) == []
    assert LAST_REPORT == {"steps": 0, "passed": 0, "failed": 0, "errors": 0}


@pytest.mark.parametrize("bad", ["broken", "nan", "inf"])
def test_e2_existing_errors_and_validation(bad: str) -> None:
    transport = FakeTransport({"MEAS:VOLT?": bad})
    drivers: dict[str, Driver] = {"meter": VoltageMeter(transport)}
    rows = run_station(drivers, [Step("rail", "meter", 4, 6), Step("again", "meter", 4, 6)])
    assert [row.status for row in rows] == ["ERROR", "ERROR"], "continue after a bad reading"
    assert all(row.value is None for row in rows)
    assert LAST_REPORT["errors"] == 2
    transport.queries.clear()
    with pytest.raises(ValueError):
        run_station(drivers, [Step("rail", "meter", 4, 6), Step("bad", "missing", 4, 6)])
    assert transport.queries == [], "validate the whole plan before any instrument I/O"
    for timeout in [0.0, -1.0, float("nan"), float("inf")]:
        with pytest.raises(ValueError):
            VoltageMeter(transport, timeout)
    assert check_limits(5, 4, 6)
    assert not check_limits(3, 4, 6)
    with pytest.raises(ValueError):
        check_limits(5, 6, 4)
