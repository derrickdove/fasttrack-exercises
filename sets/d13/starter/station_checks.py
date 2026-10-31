"""E4: a fake station run with one pass, one failed check and one setup error."""
from collections.abc import Callable

import pytest

STATION_ID = "CHASSIS-A1"
SERIAL_NUMBER = "SN-0042"


@pytest.fixture
def station_ready(
    request: pytest.FixtureRequest,
    record_property: Callable[[str, object], None],
) -> None:
    """Record station_id/serial_number before raising RuntimeError for offline mode."""
    raise NotImplementedError("E4: record both metadata properties, then reject offline setup")


# E4: add the three-row parametrize decorator described in the README.
def test_e4_voltage(station_ready: None, voltage: float) -> None:
    """Require the measured voltage to be within the inclusive 4.8..5.2 V limits."""
    raise NotImplementedError("E4: assert that the voltage is within the station limits")
