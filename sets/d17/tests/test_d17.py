from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

import pyvisa
from pyvisa.errors import VisaIOError
from pyvisa.resources import MessageBasedResource
import pytest
import yaml

from starter.visa_basics import identify, list_instruments, open_resource, read_voltage


STATION = Path(__file__).resolve().parents[1] / "data" / "station.yaml"
DMM = "GPIB0::8::INSTR"
PSU = "GPIB0::12::INSTR"


@pytest.fixture
def manager():
    # PyVISA shares managers for the same backend; close all sessions after each test.
    with closing(pyvisa.ResourceManager(f"{STATION}@sim")) as resource_manager:
        yield resource_manager


@pytest.fixture(params=[
    (DMM, {"manufacturer": "Fasttrack", "model": "DMM-100", "serial": "DMM001", "firmware": "1.0"}, 2.5),
    (PSU, {"manufacturer": "Fasttrack", "model": "PSU-200", "serial": "PSU002", "firmware": "2.1"}, 12.0),
], ids=["dmm", "psu"])
def instrument(request, manager):
    name, identity, voltage = request.param
    with manager.open_resource(
        name, read_termination="\n", write_termination="\n", timeout=2000
    ) as resource:
        yield resource, identity, voltage


@pytest.mark.parametrize("name", [DMM, PSU])
def test_e1_opens_and_configures_instrument(name, manager):
    resource = open_resource(name, str(STATION))
    try:
        assert isinstance(resource, MessageBasedResource), "Return the open instrument, not its manager"
        assert resource.resource_name == name, "Open the resource name requested by the operator"
        assert resource.read_termination == "\n", "Replies end with a newline"
        assert resource.write_termination == "\n", "Commands must end with a newline"
        assert resource.timeout == 2000, "The station timeout must be 2000 milliseconds"
    finally:
        resource.close()


def test_e1_returned_session_stays_open(manager):
    resource = open_resource(DMM, str(STATION))
    try:
        assert resource.query("*IDN?") == "Fasttrack,DMM-100,DMM001,1.0"
        assert resource.query("MEAS:VOLT:DC?") == "+2.500000E+00"
    finally:
        resource.close()


def test_e1_uses_supplied_file_with_spaces(tmp_path):
    station = tmp_path / "alternate station.yaml"
    station.write_text(STATION.read_text(encoding="utf-8").replace("DMM001", "ALT099"), encoding="utf-8")
    with closing(pyvisa.ResourceManager(f"{station}@sim")):
        resource = open_resource(DMM, str(station))
        try:
            assert resource.query("*IDN?") == "Fasttrack,DMM-100,ALT099,1.0", "Use sim_file, not a built-in simulation"
        finally:
            resource.close()


def test_e2_identifies_each_simulated_instrument(instrument):
    resource, expected, _ = instrument
    assert identify(resource) == expected, "Preserve the four instrument identification fields"
    assert identify(resource) == expected, "Leave the session open for the next station step"


@pytest.mark.parametrize("reply, expected", [
    ("  Bench Works , DMM X , 00042 , rev 3 \r\n", {"manufacturer": "Bench Works", "model": "DMM X", "serial": "00042", "firmware": "rev 3"}),
    ("Lab,PSU,0,0", {"manufacturer": "Lab", "model": "PSU", "serial": "0", "firmware": "0"}),
])
def test_e2_strips_fields_and_queries_once(reply, expected):
    resource = Mock(spec=MessageBasedResource)
    resource.query.return_value = reply
    assert identify(resource) == expected, "Strip surrounding whitespace, preserving field contents"
    resource.query.assert_called_once_with("*IDN?")
    resource.close.assert_not_called()


@pytest.mark.parametrize("reply", ["", "Lab,DMM,42", "Lab,DMM,42,1,extra", "Lab, ,42,1", "Lab,DMM,42,"])
def test_e2_rejects_malformed_identification(reply):
    resource = Mock(spec=MessageBasedResource)
    resource.query.return_value = reply
    with pytest.raises(ValueError):
        identify(resource)


def test_e2_propagates_query_errors():
    resource = Mock(spec=MessageBasedResource)
    error = VisaIOError(pyvisa.constants.StatusCode.error_timeout)
    resource.query.side_effect = error
    with pytest.raises(VisaIOError) as caught:
        identify(resource)
    assert caught.value is error, "Let the caller handle the original communication error"


def test_e3_reads_each_simulated_instrument(instrument):
    resource, _, expected = instrument
    result = read_voltage(resource)
    assert type(result) is float, "Return a float in volts"
    assert result == pytest.approx(expected), "Convert the actual reply from this instrument"
    assert read_voltage(resource) == pytest.approx(expected), "Keep the session open"


@pytest.mark.parametrize("reply, expected", [(" -1.25e-3\n", -0.00125), ("0", 0.0), ("+12.000", 12.0)])
def test_e3_queries_once_and_converts_numeric_text(reply, expected):
    resource = Mock(spec=MessageBasedResource)
    resource.query.return_value = reply
    result = read_voltage(resource)
    assert type(result) is float
    assert result == pytest.approx(expected)
    resource.query.assert_called_once_with("MEAS:VOLT:DC?")
    resource.close.assert_not_called()


@pytest.mark.parametrize("reply", ["", "OVERLOAD", "5 V"])
def test_e3_rejects_nonnumeric_replies(reply):
    resource = Mock(spec=MessageBasedResource)
    resource.query.return_value = reply
    with pytest.raises(ValueError):
        read_voltage(resource)


def test_e3_propagates_query_errors():
    resource = Mock(spec=MessageBasedResource)
    error = VisaIOError(pyvisa.constants.StatusCode.error_timeout)
    resource.query.side_effect = error
    with pytest.raises(VisaIOError) as caught:
        read_voltage(resource)
    assert caught.value is error, "Let the station decide whether to retry a failed query"


def test_e4_lists_sorted_station_resources():
    result = list_instruments(str(STATION))
    assert result == [PSU, DMM], "Sort resource names as strings, not by numeric bus address"
    assert type(result) is list, "Convert the manager's tuple into a list"


@pytest.mark.parametrize("names", [["GPIB0::4::INSTR"], ["GPIB0::9::INSTR", "GPIB0::2::INSTR", "GPIB0::10::INSTR"]])
def test_e4_reads_resource_names_from_supplied_file(tmp_path, names):
    document = yaml.safe_load(STATION.read_text(encoding="utf-8"))
    document["resources"] = {name: {"device": "dmm"} for name in names}
    station = tmp_path / "operator station.yaml"
    station.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    assert list_instruments(str(station)) == sorted(names), "Discover names instead of hard-coding the supplied station"


def test_e4_can_repeat_discovery():
    first = list_instruments(str(STATION))
    second = list_instruments(str(STATION))
    assert first == second == [PSU, DMM], "Discovery must work again after closing its manager"


def test_e4_handles_empty_resource_tuple_and_closes_manager():
    manager = Mock()
    manager.list_resources.return_value = ()
    with patch("starter.visa_basics.pyvisa.ResourceManager", return_value=manager) as factory:
        assert list_instruments("empty station.yaml") == [], "An empty discovery result becomes an empty list"
    factory.assert_called_once_with("empty station.yaml@sim")
    manager.list_resources.assert_called_once_with()
    manager.close.assert_called_once_with()
