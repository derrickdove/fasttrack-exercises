"""Contracts for drivers used by a chassis test station."""
import pytest

from starter.driver import Dmm, FakeTransport, PowerSupply, Transport


class RecordingTransport:
    """Independent protocol implementation recording writes and queries together."""

    def __init__(self, replies: dict[str, str]) -> None:
        self.replies = replies
        self.events: list[tuple[str, str]] = []

    def write(self, command: str) -> None:
        self.events.append(("write", command))

    def query(self, command: str) -> str:
        self.events.append(("query", command))
        return self.replies[command]


@pytest.fixture
def transport() -> RecordingTransport:
    return RecordingTransport({
        "*IDN?": "  BenchCo,DMM,17,1.0\r\n",
        "MEAS:VOLT:DC?": " +1.250E+1\r\n",
        "MEAS:VOLT?": " 3.300\n",
    })


def test_e1_writes_preserve_exact_commands() -> None:
    fake = FakeTransport({})
    assert fake.writes == [], "a new station fake must start with no writes"
    commands = ["CONF:VOLT:DC", "", "  OUTP OFF\n", "CONF:VOLT:DC"]
    for command in commands:
        assert fake.write(command) is None, "write should return None"
    assert fake.writes == commands, "preserve command text, duplicates, and call order"


def test_e1_queries_are_repeatable_and_preserve_reply_text() -> None:
    fake = FakeTransport({"*IDN?": " BenchCo\n", "MEAS:VOLT?": "", "": "empty command"})
    for command, expected in [("*IDN?", " BenchCo\n"), ("MEAS:VOLT?", ""),
                              ("*IDN?", " BenchCo\n"), ("", "empty command")]:
        assert fake.query(command) == expected, f"wrong scripted reply for {command!r}"
    assert fake.writes == [], "queries must not be recorded as writes"


@pytest.mark.parametrize("unknown", ["UNKNOWN?", "*idn?", "*IDN?\n"])
def test_e1_unknown_query_raises_without_changing_writes(unknown: str) -> None:
    fake = FakeTransport({"*IDN?": "BenchCo"})
    fake.write("CONF:VOLT:DC")
    with pytest.raises(KeyError):
        fake.query(unknown)
    assert fake.writes == ["CONF:VOLT:DC"], "failed queries must preserve history"


def test_e1_instances_have_separate_write_lists() -> None:
    first = FakeTransport({"*IDN?": "meter A"})
    second = FakeTransport({"*IDN?": "meter B"})
    compatible: Transport = first
    compatible.write("CONF:VOLT:DC")
    assert second.writes == [], "one instrument's writes must not leak into another"
    assert first.query("*IDN?") == "meter A"
    assert second.query("*IDN?") == "meter B"


def test_e2_construction_and_idn_use_injected_transport(transport: RecordingTransport) -> None:
    meter = Dmm(transport)
    assert transport.events == [], "constructing a meter must not contact hardware"
    assert meter.idn() == "BenchCo,DMM,17,1.0", "strip only surrounding ID reply whitespace"
    transport.replies["*IDN?"] = "next meter"
    assert meter.idn() == "next meter", "each identification must query the transport again"
    assert transport.events == [("query", "*IDN?"), ("query", "*IDN?")]


@pytest.mark.parametrize("reply, expected", [
    (" +1.250E+1\r\n", 12.5), ("-0.002", -0.002), ("0", 0.0),
])
def test_e2_dc_voltage_converts_reply(reply: str, expected: float,
                                    transport: RecordingTransport) -> None:
    transport.replies["MEAS:VOLT:DC?"] = reply
    meter = Dmm(transport)
    result = meter.measure_dc_voltage()
    assert isinstance(result, float), "meter readings must be floats"
    assert result == pytest.approx(expected), f"wrong voltage for reply {reply!r}"
    transport.replies["MEAS:VOLT:DC?"] = "2.75"
    assert meter.measure_dc_voltage() == 2.75, "do not cache a previous station reading"
    assert transport.events == [("query", "MEAS:VOLT:DC?"), ("query", "MEAS:VOLT:DC?")]


@pytest.mark.parametrize("reply", ["OVERLOAD", "", "1.25 V"])
def test_e2_bad_numeric_reply_reaches_caller(reply: str, transport: RecordingTransport) -> None:
    transport.replies["MEAS:VOLT:DC?"] = reply
    meter = Dmm(transport)
    with pytest.raises(ValueError):
        meter.measure_dc_voltage()
    assert transport.events == [("query", "MEAS:VOLT:DC?")]


@pytest.mark.parametrize("method, command", [("idn", "*IDN?"),
                                            ("measure_dc_voltage", "MEAS:VOLT:DC?")])
def test_e2_missing_reply_reaches_caller(method: str, command: str) -> None:
    transport = RecordingTransport({})
    meter = Dmm(transport)
    with pytest.raises(KeyError):
        getattr(meter, method)()
    assert transport.events == [("query", command)]


@pytest.mark.parametrize("ch, voltage, formatted", [
    (1, 0.0, "0.000"), (2, 30.0, "30.000"), (3, 5.1256, "5.126"),
    (1, 0.0004, "0.000"), (2, 29.9994, "29.999"),
])
def test_e3_set_voltage_exact_sequence(ch: int, voltage: float, formatted: str,
                                      transport: RecordingTransport) -> None:
    supply = PowerSupply(transport)
    assert transport.events == [], "constructing a supply must not contact hardware"
    assert supply.set_voltage(ch, voltage) is None
    assert transport.events == [("write", f"INST:NSEL {ch}"), ("write", f"VOLT {formatted}")], (
        "select the channel first, then write voltage with exactly three decimal places"
    )


@pytest.mark.parametrize("ch, voltage", [
    (0, 5.0), (4, 5.0), (-1, 5.0), (1, -0.0001), (2, 30.0001),
    (3, float("inf")), (1, float("-inf")), (2, float("nan")), (0, 31.0),
])
def test_e3_invalid_request_has_no_transport_effect(ch: int, voltage: float,
                                                  transport: RecordingTransport) -> None:
    supply = PowerSupply(transport)
    with pytest.raises(ValueError):
        supply.set_voltage(ch, voltage)
    assert transport.events == [], "validate channel AND voltage before selecting a channel"


def test_e3_rejected_request_preserves_existing_station_history(transport: RecordingTransport) -> None:
    supply = PowerSupply(transport)
    supply.set_voltage(3, 12.0)
    before = list(transport.events)
    with pytest.raises(ValueError):
        supply.set_voltage(2, -1.0)
    assert transport.events == before, "rejecting a request must leave earlier commands intact"
    supply.set_voltage(3, 12.0)
    assert transport.events == before + before, "every valid call must send its two commands"


@pytest.mark.parametrize("ch, on, command", [
    (1, True, "OUTP ON"), (2, False, "OUTP OFF"), (3, True, "OUTP ON"),
])
def test_e4_output_exact_sequence(ch: int, on: bool, command: str,
                                  transport: RecordingTransport) -> None:
    supply = PowerSupply(transport)
    assert supply.output(ch, on) is None
    assert transport.events == [("write", f"INST:NSEL {ch}"), ("write", command)]


@pytest.mark.parametrize("ch, reply, expected", [(1, "0", 0.0), (2, " 3.300\n", 3.3),
                                               (3, "-2.5E-3", -0.0025)])
def test_e4_measure_selects_before_query(ch: int, reply: str, expected: float,
                                       transport: RecordingTransport) -> None:
    transport.replies["MEAS:VOLT?"] = reply
    supply = PowerSupply(transport)
    result = supply.measure_voltage(ch)
    assert isinstance(result, float), "supply readings must be floats"
    assert result == pytest.approx(expected), f"wrong supply reading for {reply!r}"
    assert transport.events == [("write", f"INST:NSEL {ch}"), ("query", "MEAS:VOLT?")], (
        "select the requested supply channel before asking for its voltage"
    )


@pytest.mark.parametrize("ch", [-1, 0, 4])
@pytest.mark.parametrize("on", [True, False])
def test_e4_invalid_output_channel_preserves_history(ch: int, on: bool,
                                                    transport: RecordingTransport) -> None:
    supply = PowerSupply(transport)
    transport.write("existing station command")
    before = list(transport.events)
    with pytest.raises(ValueError):
        supply.output(ch, on)
    assert transport.events == before, "invalid output channel must cause no transport calls"


@pytest.mark.parametrize("ch", [-1, 0, 4])
def test_e4_invalid_measure_channel_does_not_query(ch: int, transport: RecordingTransport) -> None:
    supply = PowerSupply(transport)
    with pytest.raises(ValueError):
        supply.measure_voltage(ch)
    assert transport.events == [], "invalid measurement channel must not write or query"


def test_e4_station_procedure_reselects_and_reads_again(transport: RecordingTransport) -> None:
    supply = PowerSupply(transport)
    supply.set_voltage(2, 5.0)
    supply.output(2, True)
    assert supply.measure_voltage(2) == 3.3
    transport.replies["MEAS:VOLT?"] = "4.9"
    assert supply.measure_voltage(3) == 4.9, "each measurement needs a fresh query"
    supply.output(2, False)
    assert transport.events == [
        ("write", "INST:NSEL 2"), ("write", "VOLT 5.000"),
        ("write", "INST:NSEL 2"), ("write", "OUTP ON"),
        ("write", "INST:NSEL 2"), ("query", "MEAS:VOLT?"),
        ("write", "INST:NSEL 3"), ("query", "MEAS:VOLT?"),
        ("write", "INST:NSEL 2"), ("write", "OUTP OFF"),
    ], "a station procedure must issue every transport call in order"


@pytest.mark.parametrize("replies, error", [({"MEAS:VOLT?": "OVERLOAD"}, ValueError),
                                          ({}, KeyError)])
def test_e4_reply_error_follows_channel_selection(replies: dict[str, str],
                                                 error: type[Exception]) -> None:
    transport = RecordingTransport(replies)
    supply = PowerSupply(transport)
    with pytest.raises(error):
        supply.measure_voltage(3)
    assert transport.events == [("write", "INST:NSEL 3"), ("query", "MEAS:VOLT?")], (
        "reply errors must reach the caller after selection, without extra commands"
    )
