"""Block 3 contracts through public driver and transport interfaces."""

from importlib import import_module
from pathlib import Path
from typing import Protocol
from unittest.mock import Mock

import pyvisa
import pytest


def test_instruments_reexports_public_names(instruments):
    for module_name, names in {
        "base": ["InstrumentError", "Transport", "VisaTransport", "parse_error"],
        "psu": ["PowerSupply"], "dmm": ["Dmm"],
        "serial_transport": ["SerialTransport"], "tcp_transport": ["TcpTransport"],
    }.items():
        module = import_module(f"chassis.instruments.{module_name}")
        for name in names:
            assert getattr(instruments, name) is getattr(module, name)


def test_transport_is_protocol_with_write_query_close(instruments):
    assert issubclass(instruments.Transport, Protocol)
    for name in ("write", "query", "close"):
        assert callable(getattr(instruments.Transport, name))


def test_instrument_error_carries_code_and_message(instruments):
    assert issubclass(instruments.InstrumentError, Exception)
    error = instruments.InstrumentError(-113, "Undefined header")
    assert (error.code, error.message) == (-113, "Undefined header")


@pytest.mark.parametrize("reply,expected", [
    ('-113,"Undefined header"', (-113, "Undefined header")),
    ('0,"No error"', (0, "No error")),
    ('-222,"Data out of range, channel 2"', (-222, "Data out of range, channel 2")),
])
def test_parse_error_returns_integer_code_and_message(instruments, reply, expected):
    assert instruments.parse_error(reply) == expected


@pytest.mark.parametrize("reply", [
    "garbage", 'oops,"Bad code"', '-113,"Unclosed', '-113,"Header",extra',
])
def test_parse_error_rejects_garbage(instruments, reply):
    with pytest.raises(ValueError):
        instruments.parse_error(reply)


@pytest.mark.parametrize("method,value,command", [
    ("set_voltage", 12.3456, "VOLT 12.346"),
    ("set_current_limit", 1.2346, "CURR 1.235"),
])
def test_psu_selects_channel_then_writes_three_decimal_setting(
    instruments, fake_factory, method, value, command,
):
    fake = fake_factory()
    getattr(instruments.PowerSupply(fake), method)(2, value)
    assert fake.events == [("write", "INST:NSEL 2"), ("write", command)]


@pytest.mark.parametrize("method,maximum,prefix", [
    ("set_voltage", 30.0, "VOLT"), ("set_current_limit", 3.0, "CURR"),
])
def test_psu_accepts_both_envelope_endpoints(instruments, fake_factory, method, maximum, prefix):
    fake = fake_factory()
    psu = instruments.PowerSupply(fake)
    getattr(psu, method)(1, 0.0)
    getattr(psu, method)(3, maximum)
    assert fake.events == [
        ("write", "INST:NSEL 1"), ("write", f"{prefix} 0.000"),
        ("write", "INST:NSEL 3"), ("write", f"{prefix} {maximum:.3f}"),
    ]


@pytest.mark.parametrize("method,value", [
    ("set_voltage", -0.001), ("set_voltage", 30.001),
    ("set_current_limit", -0.001), ("set_current_limit", 3.001),
])
def test_psu_rejects_out_of_range_setting_before_any_write(instruments, fake_factory, method, value):
    fake = fake_factory()
    with pytest.raises(ValueError):
        getattr(instruments.PowerSupply(fake), method)(1, value)
    assert fake.events == [], "validate the setting before selecting a channel"


@pytest.mark.parametrize("channel", [0, 4])
def test_psu_rejects_invalid_channel_for_every_channel_method(instruments, fake_factory, channel):
    fake = fake_factory()
    psu = instruments.PowerSupply(fake)
    for method, args in [
        (psu.set_voltage, (channel, 12.0)),
        (psu.set_current_limit, (channel, 1.0)),
        (psu.output, (channel, True)), (psu.measure_voltage, (channel,)),
    ]:
        with pytest.raises(ValueError):
            method(*args)
        assert fake.events == [], "invalid channels must cause no transport operations"


def test_psu_output_selects_channel_and_sends_on_or_off(instruments, fake_factory):
    fake = fake_factory()
    psu = instruments.PowerSupply(fake)
    psu.output(1, True)
    psu.output(3, False)
    assert fake.events == [
        ("write", "INST:NSEL 1"), ("write", "OUTP ON"),
        ("write", "INST:NSEL 3"), ("write", "OUTP OFF"),
    ]


@pytest.mark.parametrize("driver", ["PowerSupply", "Dmm"])
def test_driver_idn_queries_identification(instruments, fake_factory, driver):
    fake = fake_factory({"*IDN?": ["FASTTRACK,INSTRUMENT,123,1.0"]})
    assert getattr(instruments, driver)(fake).idn() == "FASTTRACK,INSTRUMENT,123,1.0"
    assert fake.events == [("query", "*IDN?")]


def test_psu_measure_voltage_selects_channel_then_queries_float(instruments, fake_factory):
    fake = fake_factory({"MEAS:VOLT?": [" 2.4125E+1\n"]})
    value = instruments.PowerSupply(fake).measure_voltage(2)
    assert isinstance(value, float)
    assert value == pytest.approx(24.125)
    assert fake.events == [("write", "INST:NSEL 2"), ("query", "MEAS:VOLT?")]


def test_dmm_measurements_use_dc_queries_and_return_floats(instruments, fake_factory):
    fake = fake_factory({"MEAS:VOLT:DC?": ["-1.25E-3"], "MEAS:CURR:DC?": [" 0.125\n"]})
    dmm = instruments.Dmm(fake)
    voltage, current = dmm.measure_dc_voltage(), dmm.measure_dc_current()
    assert isinstance(voltage, float) and isinstance(current, float)
    assert voltage == pytest.approx(-0.00125)
    assert current == pytest.approx(0.125)
    assert fake.events == [("query", "MEAS:VOLT:DC?"), ("query", "MEAS:CURR:DC?")]


@pytest.mark.parametrize("driver", ["PowerSupply", "Dmm"])
def test_check_errors_stops_on_zero_and_returns_none(instruments, fake_factory, driver):
    fake = fake_factory({"SYST:ERR?": ['0,"No error"', '-113,"Must not read this"']})
    assert getattr(instruments, driver)(fake).check_errors() is None
    assert fake.events == [("query", "SYST:ERR?")]


@pytest.mark.parametrize("driver", ["PowerSupply", "Dmm"])
def test_check_errors_drains_queue_then_raises_first_error(instruments, fake_factory, driver):
    fake = fake_factory({"SYST:ERR?": [
        '-113,"Undefined header"', '-222,"Data out of range"', '0,"No error"',
    ]})
    with pytest.raises(instruments.InstrumentError) as caught:
        getattr(instruments, driver)(fake).check_errors()
    assert (caught.value.code, caught.value.message) == (-113, "Undefined header")
    assert fake.events == [("query", "SYST:ERR?")] * 3


@pytest.mark.parametrize("driver", ["PowerSupply", "Dmm"])
def test_check_errors_caps_nonzero_queue_at_twenty_reads(instruments, fake_factory, driver):
    fake = fake_factory({"SYST:ERR?": ['-113,"First error"'] + ['-222,"Later error"'] * 20})
    with pytest.raises(instruments.InstrumentError) as caught:
        getattr(instruments, driver)(fake).check_errors()
    assert (caught.value.code, caught.value.message) == (-113, "First error")
    assert fake.events == [("query", "SYST:ERR?")] * 20


@pytest.mark.parametrize("channels", [1, 3])
def test_psu_context_turns_off_configured_channels_without_closing_transport(
    instruments, fake_factory, channels,
):
    fake = fake_factory()
    psu = instruments.PowerSupply(fake) if channels == 3 else instruments.PowerSupply(fake, channels=channels)
    with psu:
        pass
    assert fake.events == [
        event for ch in range(1, channels + 1)
        for event in [("write", f"INST:NSEL {ch}"), ("write", "OUTP OFF")]
    ]
    assert not fake.closed, "the caller owns the transport"


def test_psu_context_turns_off_all_outputs_after_body_exception(instruments, fake_factory):
    fake = fake_factory()
    original = RuntimeError("test step failed")
    with pytest.raises(RuntimeError) as caught:
        with instruments.PowerSupply(fake):
            raise original
    assert caught.value is original
    assert fake.events == [
        event for ch in range(1, 4)
        for event in [("write", f"INST:NSEL {ch}"), ("write", "OUTP OFF")]
    ]
    assert not fake.closed


def test_psu_context_propagates_teardown_error_and_attempts_remaining_outputs(instruments, fake_factory):
    fake = fake_factory()
    fake.fail_first_off = True
    with pytest.raises(OSError, match="output shutdown failed"):
        with instruments.PowerSupply(fake):
            pass
    assert fake.events == [
        event for ch in range(1, 4)
        for event in [("write", f"INST:NSEL {ch}"), ("write", "OUTP OFF")]
    ]
    assert not fake.closed


def test_psu_context_preserves_body_error_when_teardown_also_fails(instruments, fake_factory):
    fake = fake_factory()
    fake.fail_first_off = True
    original = RuntimeError("test step failed")
    with pytest.raises(RuntimeError) as caught:
        with instruments.PowerSupply(fake):
            raise original
    assert caught.value is original
    assert fake.events == [
        event for ch in range(1, 4)
        for event in [("write", f"INST:NSEL {ch}"), ("write", "OUTP OFF")]
    ]
    assert not fake.closed


@pytest.mark.parametrize("custom", [False, True], ids=["defaults", "custom-options"])
@pytest.mark.parametrize("shared_manager", [False, True], ids=["separate-managers", "cached-manager"])
def test_visa_transport_configures_queries_writes_and_closes_both_owners(
    import_isolated_instruments, monkeypatch, custom, shared_manager,
):
    def make_resource():
        resource = Mock(spec=pyvisa.resources.MessageBasedResource)
        resource.events = []
        resource.closed = False
        resource.write.side_effect = lambda cmd: resource.events.append(("write", cmd))

        def query(cmd):
            resource.events.append(("query", cmd))
            return " \tFASTTRACK,PSU,123,1.0\r\n"

        def close():
            resource.closed = True

        resource.query.side_effect = query
        resource.close.side_effect = close
        return resource

    class Manager:
        def __init__(self):
            self.resources = []
            self.names = []
            self.closed = False

        def open_resource(self, name, **kwargs):
            self.names.append(name)
            resource = make_resource()
            self.resources.append(resource)
            return resource

        def close(self):
            assert all(resource.closed for resource in self.resources), "close resources before their manager"
            self.closed = True

    managers, backends = [], []

    def resource_manager(backend=""):
        backends.append(backend)
        manager = managers[-1] if shared_manager and managers and not managers[-1].closed else Manager()
        managers.append(manager)
        return manager

    monkeypatch.setattr(pyvisa, "ResourceManager", resource_manager)
    instruments = import_isolated_instruments()
    options = dict(backend="custom@sim", timeout_ms=321, read_termination="\r", write_termination="\r\n") if custom else {}
    transport = instruments.VisaTransport("GPIB::1::INSTR", **options)
    manager = managers[-1]
    resource = manager.resources[-1]
    assert backends == ["custom@sim" if custom else ""]
    assert manager.names == ["GPIB::1::INSTR"]
    assert (resource.timeout, resource.read_termination, resource.write_termination) == (
        (321, "\r", "\r\n") if custom else (2000, "\n", "\n")
    )
    assert transport.write("OUTP OFF") is None
    assert transport.query("*IDN?") == "FASTTRACK,PSU,123,1.0"
    assert resource.events == [("write", "OUTP OFF"), ("query", "*IDN?")]
    other = instruments.VisaTransport("GPIB::2::INSTR", **options)
    assert len(managers) == 2, "each transport must create its own manager"
    assert backends == ["custom@sim" if custom else ""] * 2
    other_manager = managers[-1]
    other_resource = other_manager.resources[-1]
    transport.close()
    assert resource.closed
    assert manager.closed is (not shared_manager)
    assert not other_resource.closed and not other_manager.closed
    assert other.query("*IDN?") == "FASTTRACK,PSU,123,1.0"
    other.close()
    assert other_resource.closed and other_manager.closed
    original = RuntimeError("body failed")
    with pytest.raises(RuntimeError) as caught:
        with instruments.VisaTransport("GPIB::2::INSTR", **options):
            raise original
    assert caught.value is original
    assert managers[-1].resources[-1].closed and managers[-1].closed


def test_psu_driver_works_through_pyvisa_sim(instruments):
    backend = str(Path(__file__).parent / "data" / "instruments.yaml") + "@sim"
    with instruments.VisaTransport("GPIB::1::INSTR", backend=backend, timeout_ms=250) as transport:
        with instruments.PowerSupply(transport) as psu:
            assert psu.idn() == "FASTTRACK,PSU,SIM,1.0"
            psu.set_voltage(2, 24.0)
            psu.set_current_limit(2, 0.5)
            psu.output(2, True)
            assert psu.measure_voltage(2) == pytest.approx(24.125)
            assert psu.check_errors() is None
        # Shutdown must also use commands the simulated instrument recognizes.
        assert transport.query("SYST:ERR?") == '0,"No error"'


def test_dmm_driver_works_through_pyvisa_sim(instruments):
    backend = str(Path(__file__).parent / "data" / "instruments.yaml") + "@sim"
    with instruments.VisaTransport("GPIB::2::INSTR", backend=backend, timeout_ms=250) as transport:
        dmm = instruments.Dmm(transport)
        assert dmm.idn() == "FASTTRACK,DMM,SIM,1.0"
        assert dmm.measure_dc_voltage() == pytest.approx(24.125)
        assert dmm.measure_dc_current() == pytest.approx(0.125)
        assert dmm.check_errors() is None


@pytest.mark.parametrize("first_closed", [0, 1], ids=["close-psu-first", "close-dmm-first"])
def test_visa_closing_one_instrument_keeps_the_other_usable(instruments, first_closed):
    backend = str(Path(__file__).parent / "data" / "instruments.yaml") + "@sim"
    transports = []
    try:
        for address in ("GPIB::1::INSTR", "GPIB::2::INSTR"):
            transports.append(instruments.VisaTransport(address, backend=backend, timeout_ms=250))
        assert instruments.PowerSupply(transports[0]).idn() == "FASTTRACK,PSU,SIM,1.0"
        assert instruments.Dmm(transports[1]).measure_dc_voltage() == pytest.approx(24.125)
        transports.pop(first_closed).close()
        survivor = transports[0]
        if first_closed == 0:
            assert instruments.Dmm(survivor).measure_dc_voltage() == pytest.approx(24.125)
        else:
            psu = instruments.PowerSupply(survivor)
            psu.set_voltage(1, 5.0)
            assert psu.measure_voltage(1) == pytest.approx(24.125)
        assert survivor.query("SYST:ERR?") == '0,"No error"'
    finally:
        for transport in transports:
            transport.close()
