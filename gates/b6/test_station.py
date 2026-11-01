"""One configured station run, including failures after passing readings."""

from importlib import import_module
import json
from types import SimpleNamespace

import pytest


class FakeTransport:
    def __init__(self, name, events, replies=None):
        self.name = name
        self.events = events
        self.replies = replies or {}
        self.failures = {}
        self.closed = False

    def write(self, cmd):
        self.events.append((self.name, "write", cmd))
        if cmd in self.failures:
            raise self.failures[cmd]

    def query(self, cmd):
        self.events.append((self.name, "query", cmd))
        reply = self.replies[cmd]
        if isinstance(reply, BaseException):
            raise reply
        return reply

    def close(self):
        self.closed = True


@pytest.fixture
def station_run(station_text, station_file, tmp_path):
    station = import_module("chassis.station")
    config_path = station_file(station_text.replace('id = "uut1"', 'id = "payload"')
                               .replace("psu_channel = 1", "psu_channel = 2"))
    limits_path = tmp_path / "limits.csv"
    limits_path.write_text("name,low,high,unit\nbus_voltage,22,30,V\nsupply_current,0,3,A\n",
                           encoding="utf-8")
    report_path = tmp_path / "station report.json"
    events = []
    psu = FakeTransport("psu", events)
    dmm = FakeTransport("dmm", events, {"MEAS:VOLT:DC?": "24.1", "MEAS:CURR:DC?": "0.5"})
    transports = {"TCPIP::10.0.0.5::5025::SOCKET": psu,
                  "TCPIP::10.0.0.6::5025::SOCKET": dmm}

    def invoke():
        return station.run_station(config_path, limits_path, report_path,
                                   uut_id="payload", transports=transports, volts=25.0, amps=0.8)

    return SimpleNamespace(invoke=invoke, psu=psu, dmm=dmm, events=events, report=report_path)


def read_report(path):
    return json.loads(path.read_text(encoding="utf-8"),
                      parse_constant=lambda token: pytest.fail(f"invalid JSON constant: {token}"))


@pytest.mark.parametrize("voltage,state", [("24.1", "PASS"), ("31.0", "FAIL")])
def test_e1_station_runs_configured_drivers_executor_checks_and_report(station_run, capsys, voltage, state):
    case = station_run
    case.dmm.replies["MEAS:VOLT:DC?"] = voltage
    run = case.invoke()
    assert run.state.name == state
    assert [(result.name, result.value, result.unit, result.status.name) for result in run.results] == [
        ("bus_voltage", float(voltage), "V", state), ("supply_current", 0.5, "A", "PASS"),
    ]
    assert case.events == [
        ("psu", "write", "INST:NSEL 2"), ("psu", "write", "VOLT 25.000"),
        ("psu", "write", "INST:NSEL 2"), ("psu", "write", "CURR 0.800"),
        ("psu", "write", "INST:NSEL 2"), ("psu", "write", "OUTP ON"),
        ("dmm", "query", "MEAS:VOLT:DC?"), ("dmm", "query", "MEAS:CURR:DC?"),
        ("psu", "write", "INST:NSEL 2"), ("psu", "write", "OUTP OFF"),
    ], "use the configured channel and drivers, with output-off after measurement"
    assert run.log[0] == "IDLE->SETUP" and run.log[-1].endswith(f"->{state}")
    document = read_report(case.report)
    assert document["summary"]["overall"] == state
    assert document["meta"] == {
        "station": "Banc \u00e9lectrique", "uut": "payload", "run_state": state, "log": run.log,
    }
    assert [result["value"] for result in document["results"]] == [float(voltage), 0.5]
    assert capsys.readouterr().out.startswith(f"OVERALL: {state} (")
    assert not case.psu.closed and not case.dmm.closed, "the caller owns both transports"


def test_e1_dmm_timeout_reports_error_and_still_sends_output_off(station_run, capsys):
    case = station_run
    case.dmm.replies["MEAS:VOLT:DC?"] = TimeoutError("DMM timed out")
    run = case.invoke()
    assert run.state.name == "ERROR"
    assert case.events[-2:] == [("psu", "write", "INST:NSEL 2"), ("psu", "write", "OUTP OFF")]
    assert sum(event == ("dmm", "query", "MEAS:VOLT:DC?") for event in case.events) == 1
    assert ("dmm", "query", "MEAS:CURR:DC?") not in case.events, "do not reuse a timed-out DMM"
    assert any("DMM timed out" in line for line in run.log)
    assert read_report(case.report)["summary"]["overall"] == "ERROR"
    output = capsys.readouterr().out
    assert output.startswith("OVERALL: ERROR (") and "OVERALL: PASS" not in output


@pytest.mark.parametrize("error", [OSError("output-off failed"), KeyboardInterrupt()],
                         ids=["cleanup-error", "cleanup-interrupt"])
def test_e1_cleanup_failure_overrides_passing_checks_for_operator_and_report(station_run, capsys, error):
    case = station_run
    case.psu.failures["OUTP OFF"] = error
    run = case.invoke()
    assert run.state.name == "ERROR"
    assert len(run.results) == 2 and all(result.status.name == "PASS" for result in run.results)
    assert case.events[-1] == ("psu", "write", "OUTP OFF")
    assert any("cleanup failed:" in line for line in run.log)
    document = read_report(case.report)
    assert document["summary"] == {"total": 2, "pass": 2, "fail": 0, "error": 0, "overall": "ERROR"}
    assert document["meta"]["run_state"] == "ERROR" and document["meta"]["log"] == run.log
    output = capsys.readouterr().out
    assert output.startswith("OVERALL: ERROR (") and "OVERALL: PASS" not in output


def test_e1_operator_interrupt_reports_aborted_and_sends_output_off(station_run, capsys):
    case = station_run
    case.dmm.replies["MEAS:VOLT:DC?"] = KeyboardInterrupt()
    run = case.invoke()
    assert run.state.name == "ABORTED"
    assert case.events[-1] == ("psu", "write", "OUTP OFF")
    assert read_report(case.report)["summary"]["overall"] == "ABORTED"
    output = capsys.readouterr().out
    assert output.startswith("OVERALL: ABORTED (") and "OVERALL: PASS" not in output


def test_e1_partial_setup_failure_still_attempts_output_off(station_run, capsys):
    case = station_run
    case.psu.failures["VOLT 25.000"] = OSError("setpoint failed")
    run = case.invoke()
    assert run.state.name == "ERROR"
    assert case.events == [
        ("psu", "write", "INST:NSEL 2"), ("psu", "write", "VOLT 25.000"),
        ("psu", "write", "INST:NSEL 2"), ("psu", "write", "OUTP OFF"),
    ]
    assert read_report(case.report)["summary"]["overall"] == "ERROR"
    assert capsys.readouterr().out.startswith("OVERALL: ERROR (")
