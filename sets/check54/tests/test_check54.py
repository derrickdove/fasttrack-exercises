"""Acceptance checks for the final offline station assessment."""
from __future__ import annotations

from io import StringIO
import json
import math
from pathlib import Path
from typing import Callable

import pytest
import pyvisa
from pyvisa.constants import StatusCode
from pyvisa.errors import VisaIOError

from starter.check54 import (
    Snapshot, StationConfig, StationSupply, VisaTimeout, audit_sequences, decode_snapshot,
    execute_steps, interlock_reasons, judge_samples, main, service_findings,
    validate_config, write_run_report,
)


@pytest.fixture
def config() -> dict[str, object]:
    return {"station": " BENCH-9 ", "timeout_ms": 250, "retries": 1,
            "channels": [" bus ", "return"]}


def test_e1_normalizes_without_mutating(config: dict[str, object]) -> None:
    got = validate_config(config)
    assert got == StationConfig("BENCH-9", 0.25, 1, ("bus", "return"))
    assert config["station"] == " BENCH-9 "
    assert config["channels"] == [" bus ", "return"]


@pytest.mark.parametrize("timeout,retries", [(1, 0), (5000, 2)])
def test_e1_boundary_values(config: dict[str, object], timeout: int, retries: int) -> None:
    config.update(timeout_ms=timeout, retries=retries, channels=["bus", "BUS"])
    got = validate_config(config)
    assert (got.timeout_s, got.retries) == (timeout / 1000, retries)
    assert got.channels == ("bus", "BUS"), "channel comparison is case-sensitive"


@pytest.mark.parametrize("field,value", [
    ("station", "  "), ("station", 42), ("timeout_ms", 0),
    ("timeout_ms", 5001), ("timeout_ms", True), ("timeout_ms", 250.0),
    ("retries", -1), ("retries", 3), ("retries", False), ("retries", "1"),
    ("channels", []), ("channels", "bus"), ("channels", ["bus", " bus "]),
    ("channels", ["bus", " "]), ("channels", ["bus", 4]),
])
def test_e1_rejects_bad_fields(config: dict[str, object], field: str, value: object) -> None:
    config[field] = value
    with pytest.raises(ValueError):
        validate_config(config)


@pytest.mark.parametrize("missing", ["station", "timeout_ms", "retries", "channels"])
def test_e1_requires_all_keys(config: dict[str, object], missing: str) -> None:
    del config[missing]
    with pytest.raises(ValueError):
        validate_config(config)


def test_e1_rejects_unknown_key(config: dict[str, object]) -> None:
    config["timout_ms"] = 250
    with pytest.raises(ValueError):
        validate_config(config)


class ScriptedResource:
    def __init__(self, replies: list[str | Exception]) -> None:
        self.timeout = 0
        self.read_termination = ""
        self.write_termination = ""
        self.replies = list(replies)
        self.events: list[tuple[object, ...]] = []
        self.write_error: OSError | None = None
        self.close_error: OSError | None = None

    def query(self, cmd: str) -> str:
        self.events.append(("query", cmd))
        assert self.replies, "driver made more queries than allowed"
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def write(self, cmd: str) -> None:
        self.events.append(("write", cmd))
        if self.write_error is not None:
            raise self.write_error

    def close(self) -> None:
        self.events.append(("close",))
        if self.close_error is not None:
            raise self.close_error


class FakeResourceManager:
    def __init__(self, resource: ScriptedResource) -> None:
        self.resource = resource
        self.opened: list[str] = []

    def open_resource(self, name: str) -> ScriptedResource:
        self.opened.append(name)
        return self.resource


@pytest.mark.parametrize("settings,timeout", [
    ({"ip": "192.0.2.45", "max_voltage": 12.5}, 2000),
    ({"ip": "bench-9", "timeout_ms": 1, "max_voltage": 1}, 1),
    ({"ip": "192.0.2.46", "timeout_ms": 6000, "max_voltage": 24}, 6000),
])
def test_e2_configures_resource_before_use(settings: dict[str, object], timeout: int) -> None:
    before = settings.copy()
    resource = ScriptedResource([])
    rm = FakeResourceManager(resource)
    supply = StationSupply.from_config(settings, rm)
    assert isinstance(supply, StationSupply)
    assert rm.opened == [f"TCPIP::{settings['ip']}::INSTR"]
    assert resource.timeout == timeout, "VISA timeout is in milliseconds"
    assert (resource.read_termination, resource.write_termination) == ("\n", "\n")
    assert resource.events == [], "configuration must not query or energize hardware"
    assert settings == before, "do not change the caller's config"
    supply.close()


@pytest.mark.parametrize("key,value,missing", [
    ("ip", None, True), ("max_voltage", None, True),
    ("ip", "", False), ("ip", 9, False), ("ip", None, False),
    ("timeout_ms", 0, False), ("timeout_ms", -1, False),
    ("timeout_ms", True, False), ("timeout_ms", False, False),
    ("timeout_ms", 2000.0, False), ("timeout_ms", "2000", False),
    ("timeout_ms", None, False), ("max_voltage", 0, False),
    ("max_voltage", -0.1, False), ("max_voltage", math.nan, False),
    ("max_voltage", math.inf, False), ("max_voltage", -math.inf, False),
    ("max_voltage", "12", False), ("max_voltage", None, False),
    ("max_voltage", True, False), ("max_voltage", False, False),
    ("timout_ms", 250, False),
])
def test_e2_invalid_config_never_opens(key: str, value: object, missing: bool) -> None:
    settings: dict[str, object] = {"ip": "192.0.2.45", "max_voltage": 12.5}
    if missing:
        del settings[key]
    else:
        settings[key] = value
    before = settings.copy()
    resource = ScriptedResource([])
    rm = FakeResourceManager(resource)
    with pytest.raises(ValueError, match=key):
        StationSupply.from_config(settings, rm)
    assert rm.opened == [], f"invalid {key} must be rejected before opening"
    assert resource.events == []
    assert settings == before


@pytest.mark.parametrize("replies,expected,queries", [
    ([" 3.3125\r\n"], 3.3125, 1), (["-2.5e-2"], -0.025, 1), (["0"], 0.0, 1),
    ([VisaTimeout("first"), "12.034"], 12.034, 2),
    ([VisaIOError(StatusCode.error_timeout), "12.034"], 12.034, 2),
    ([VisaIOError(StatusCode.error_timeout), VisaIOError(StatusCode.error_timeout)], VisaIOError, 2),
    ([VisaIOError(StatusCode.error_resource_not_found)], VisaIOError, 1),
    ([VisaIOError(StatusCode.error_timeout), VisaIOError(StatusCode.error_resource_not_found)], VisaIOError, 2),
    ([VisaIOError(StatusCode.error_timeout), "bad"], ValueError, 2),
    ([VisaTimeout("first"), VisaTimeout("second")], VisaTimeout, 2),
    ([OSError("link down")], OSError, 1),
    ([TimeoutError("not VisaTimeout")], TimeoutError, 1),
    (["bad"], ValueError, 1), ([""], ValueError, 1), (["3.3 V"], ValueError, 1),
    ([VisaTimeout("first"), "bad"], ValueError, 2),
    ([VisaTimeout("first"), OSError("link down")], OSError, 2),
])
def test_e2_reads_and_retries_only_visa_timeout(
    replies: list[str | Exception], expected: float | type[Exception], queries: int,
) -> None:
    resource = ScriptedResource(replies)
    supply = StationSupply.from_config(
        {"ip": "192.0.2.45", "max_voltage": 12.5}, FakeResourceManager(resource),
    )
    if isinstance(expected, type):
        with pytest.raises(expected) as caught:
            supply.read_voltage()
        if isinstance(replies[-1], Exception):
            assert caught.value is replies[-1], "propagate the resource's exception"
    else:
        assert supply.read_voltage() == pytest.approx(expected)
    assert resource.events == [("query", "MEAS:VOLT?")] * queries
    supply.close()


@pytest.mark.parametrize("maximum,volts,command", [
    (12.5, 0.0, "VOLT 0.000"), (12.5, 12.5, "VOLT 12.500"),
    (12.5, 3.3125, "VOLT 3.312"), (12.5, -0.001, None),
    (12.5, 12.5001, "VOLT 12.500"), (12.5, -0.0001, "VOLT -0.000"),
    (12.5, 12.501, None), (12.5, math.nan, None),
    (12.5, math.inf, None), (12.5, -math.inf, None),
    (12.3456, 12.3456, None), (12.3456, 12.345, "VOLT 12.345"),
    (12.3454, 12.3454, "VOLT 12.345"),
])
def test_e2_commands_validate_before_writing(
    maximum: float, volts: float, command: str | None,
) -> None:
    resource = ScriptedResource([])
    supply = StationSupply.from_config(
        {"ip": "192.0.2.45", "max_voltage": maximum}, FakeResourceManager(resource),
    )
    if command is None:
        with pytest.raises(ValueError):
            supply.set_voltage(volts)
        assert resource.events == [], "unsafe voltage must never reach the instrument"
    else:
        supply.set_voltage(volts)
        assert resource.events == [("write", command)]
    resource.events.clear()
    supply.enable_output(True)
    supply.enable_output(False)
    assert resource.events == [("write", "OUTP 1"), ("write", "OUTP 0")]
    for bad in (0, 1, 2, "1", None, 1.0, [], object()):
        with pytest.raises(TypeError):
            supply.enable_output(bad)
    assert resource.events == [("write", "OUTP 1"), ("write", "OUTP 0")], "bad flags must not write"
    supply.close()
    supply.close()
    assert resource.events[-1:] == [("close",)]
    assert resource.events.count(("close",)) == 1, "close must be idempotent"


@pytest.mark.parametrize("block_error", [None, RuntimeError("step failed"), KeyboardInterrupt()])
@pytest.mark.parametrize("write_fails,close_fails", [(False, False), (True, False), (False, True), (True, True)])
def test_e2_context_disables_then_closes_and_preserves_block_error(
    block_error: BaseException | None, write_fails: bool, close_fails: bool,
) -> None:
    resource = ScriptedResource([])
    resource.write_error = OSError("cannot disable") if write_fails else None
    resource.close_error = OSError("cannot close") if close_fails else None
    supply = StationSupply.from_config(
        {"ip": "192.0.2.45", "max_voltage": 12.5}, FakeResourceManager(resource),
    )

    def run_block() -> None:
        with supply as entered:
            assert entered is supply, "__enter__ returns the supply"
            if block_error is not None:
                raise block_error

    expected = block_error or resource.close_error or resource.write_error
    if expected is None:
        run_block()
    else:
        with pytest.raises(type(expected)) as caught:
            run_block()
        assert caught.value is expected, "a block exception must survive cleanup failures"
    assert resource.events == [("write", "OUTP 0"), ("close",)]
    supply.close()
    assert resource.events == [("write", "OUTP 0"), ("close",)], "exit already closed the supply"


def test_e2_real_pyvisa_sim_resource() -> None:
    definition = Path(__file__).resolve().parents[1] / "data" / "station_supply.yaml"
    rm = pyvisa.ResourceManager(f"{definition}@sim")
    try:
        with StationSupply.from_config({"ip": "192.0.2.45", "max_voltage": 12.5}, rm) as supply:
            supply.set_voltage(3.3125)
            supply.enable_output(True)
            assert supply.read_voltage() == 3.3125
    finally:
        rm.close()


@pytest.mark.parametrize("samples,required,expected", [
    ([3.0, 3.3, 3.6], 3, "PASS"), ([3.3] * 5, 2, "PASS"),
    ([3.3, 3.61], 2, "FAIL"), ([2.99, 3.3], 2, "FAIL"),
    ([3.3, 3.3, 9.0], 2, "FAIL"), ([3.3], 2, "INCOMPLETE"),
    ([], 1, "INCOMPLETE"), ([99.0], 2, "INCOMPLETE"),
])
def test_e3_result_states(samples: list[float], required: int, expected: str) -> None:
    assert judge_samples(samples, 3.0, 3.6, required) == expected


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_e3_invalid_measurement_has_highest_priority(bad: float) -> None:
    assert judge_samples([bad], 3.0, 3.6, 3) == "ERROR"
    assert judge_samples([0.0, bad], 3.0, 3.6, 1) == "ERROR"


@pytest.mark.parametrize("low,high,required", [
    (4.0, 3.0, 1), (math.nan, 3.0, 1), (0.0, math.inf, 1),
    (-math.inf, 3.0, 1), (0.0, 3.0, 0), (0.0, 3.0, -1),
])
def test_e3_invalid_limits(low: float, high: float, required: int) -> None:
    with pytest.raises(ValueError):
        judge_samples([], low, high, required)


def test_e3_equal_limits_and_input_preservation() -> None:
    samples = [3.3, 3.3]
    assert judge_samples(samples, 3.3, 3.3, 2) == "PASS"
    assert samples == [3.3, 3.3]


@pytest.mark.parametrize("hex_packet,expected", [
    ("4643002a0ce409ce", Snapshot(42, 3.3, True, True)),
    ("4643010212340121", Snapshot(258, 4.66, True, False)),
    ("4643000000000005", Snapshot(0, 0.0, False, False)),
    ("4643ffffffff0005", Snapshot(65535, 65.535, False, False)),
    ("464300000000080d", Snapshot(0, 0.0, False, True)),
])
def test_e4_decodes_fixed_wire_examples(hex_packet: str, expected: Snapshot) -> None:
    got = decode_snapshot(bytes.fromhex(hex_packet))
    assert got.voltage_v == pytest.approx(expected.voltage_v)
    assert got.sequence == expected.sequence
    assert got.output_on == expected.output_on
    assert got.overtemp == expected.overtemp


@pytest.mark.parametrize("packet", [b"", b"FC", bytes(7), bytes(9)])
def test_e4_requires_exact_length(packet: bytes) -> None:
    with pytest.raises(ValueError):
        decode_snapshot(packet)


def test_e4_checksum_detects_payload_corruption() -> None:
    packet = bytearray.fromhex("4643002a0ce409ce")
    packet[4] ^= 1
    with pytest.raises(ValueError):
        decode_snapshot(bytes(packet))


@pytest.mark.parametrize("hex_packet", ["4743000000000004", "4643000000000207"])
def test_e4_checks_magic_and_reserved_bits_even_with_good_checksum(hex_packet: str) -> None:
    with pytest.raises(ValueError):
        decode_snapshot(bytes.fromhex(hex_packet))


@pytest.mark.parametrize("sequences,expected", [
    ([], {"accepted": 0, "missing": 0, "duplicates": 0, "stale": 0}),
    ([900], {"accepted": 1, "missing": 0, "duplicates": 0, "stale": 0}),
    ([5, 6, 10, 10, 11], {"accepted": 4, "missing": 3, "duplicates": 1, "stale": 0}),
])
def test_e5_empty_first_and_forward(sequences: list[int], expected: dict[str, int]) -> None:
    assert audit_sequences(sequences) == expected


def test_e5_wraparound_duplicate_and_stale() -> None:
    sequence = [65534, 0, 0, 65535, 2, 32770, 3]
    assert audit_sequences(sequence) == {"accepted": 4, "missing": 2, "duplicates": 1, "stale": 2}
    assert sequence == [65534, 0, 0, 65535, 2, 32770, 3]


def test_e5_half_range_boundary_does_not_move_baseline() -> None:
    assert audit_sequences([10, 32778, 11, 10, 11]) == {
        "accepted": 2, "missing": 0, "duplicates": 1, "stale": 2,
    }
    assert audit_sequences([0, 32767]) == {
        "accepted": 2, "missing": 32766, "duplicates": 0, "stale": 0,
    }


@pytest.mark.parametrize("sequences", [[-1], [65536], [1, -1]])
def test_e5_rejects_out_of_range(sequences: list[int]) -> None:
    with pytest.raises(ValueError):
        audit_sequences(sequences)


def test_e6_order_and_success_cleanup() -> None:
    events: list[str] = []

    def step(name: str) -> Callable[[], str]:
        def action() -> str:
            events.append(name)
            return "PASS"
        return action

    assert execute_steps([("rail", step("rail")), ("load", step("load"))],
                         lambda: events.append("cleanup")) == [("rail", "PASS"), ("load", "PASS")]
    assert events == ["rail", "load", "cleanup"]


@pytest.mark.parametrize("outcome,expected", [("FAIL", "FAIL"), ("unknown", "ERROR")])
def test_e6_stop_and_skip(outcome: str, expected: str) -> None:
    events: list[str] = []

    def forbidden() -> str:
        events.append("forbidden")
        return "PASS"

    got = execute_steps([("rail", lambda: outcome), ("load", forbidden), ("sense", forbidden)],
                        lambda: events.append("cleanup"))
    assert got == [("rail", expected), ("load", "SKIP"), ("sense", "SKIP")]
    assert events == ["cleanup"], "steps after the stopping result must never run"


def test_e6_step_exception_becomes_error() -> None:
    events: list[str] = []

    def disconnected() -> str:
        raise OSError("instrument disconnected")

    assert execute_steps([("rail", lambda: "PASS"), ("load", disconnected), ("sense", lambda: "PASS")],
                         lambda: events.append("cleanup")) == [
        ("rail", "PASS"), ("load", "ERROR"), ("sense", "SKIP"),
    ]
    assert events == ["cleanup"]


def test_e6_empty_sequence_still_cleans_up() -> None:
    events: list[str] = []
    assert execute_steps([], lambda: events.append("cleanup")) == []
    assert events == ["cleanup"]


def test_e6_cleanup_error_is_visible() -> None:
    def broken_cleanup() -> None:
        raise OSError("cleanup failed")

    with pytest.raises(OSError, match="cleanup failed"):
        execute_steps([("rail", lambda: "PASS")], broken_cleanup)



def test_e6_operator_interrupt_propagates_after_cleanup() -> None:
    events: list[str] = []

    def interrupted() -> str:
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        execute_steps([("rail", interrupted)], lambda: events.append("cleanup"))
    assert events == ["cleanup"]


def test_e7_report_structure_and_parent_creation(tmp_path: Path) -> None:
    path = tmp_path / "shift logs" / "run.json"
    rows = [("sense", "PASS"), ("rail", "FAIL")]
    mapping = {"REQ-B": ["rail"], "REQ-A": ["sense"]}
    write_run_report(path, "BENCH-9", rows, mapping)
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "station": "BENCH-9", "steps": [{"name": "sense", "status": "PASS"},
                                          {"name": "rail", "status": "FAIL"}],
        "requirements": {"REQ-A": "PASS", "REQ-B": "FAIL"},
    }
    assert rows == [("sense", "PASS"), ("rail", "FAIL")]
    assert mapping == {"REQ-B": ["rail"], "REQ-A": ["sense"]}


def test_e7_requirement_priority_and_missing_evidence(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    rows = [("a", "PASS"), ("b", "FAIL"), ("c", "ERROR"), ("d", "SKIP")]
    write_run_report(path, "S", rows, {
        "error": ["a", "b", "c", "d"], "fail": ["b", "missing"],
        "skip": ["a", "d"], "missing": ["not-executed"], "empty": [], "pass": ["a"],
    })
    assert json.loads(path.read_text(encoding="utf-8"))["requirements"] == {
        "error": "ERROR", "fail": "FAIL", "skip": "NOT_RUN",
        "missing": "NOT_RUN", "empty": "NOT_RUN", "pass": "PASS",
    }


def test_e7_format_and_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    path.write_text("old report", encoding="utf-8")
    write_run_report(path, "S", [], {})
    expected = ('{\n  "requirements": {},\n  "station": "S",\n  "steps": []\n}\n').encode("utf-8")
    assert path.read_bytes() == expected, "use two-space indentation, sorted keys and one LF at the end"


def test_e7_file_errors_propagate(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        write_run_report(tmp_path, "S", [], {})


@pytest.mark.parametrize("status,code", [("PASS", 0), ("FAIL", 1), ("ERROR", 2), ("odd", 2)])
def test_e8_status_and_exit_code(status: str, code: int) -> None:
    calls: list[Path] = []
    out, err = StringIO(), StringIO()

    def run(path: Path) -> str:
        calls.append(path)
        return status

    assert main(["--config", "shift config.toml"], run, out, err) == code
    assert calls == [Path("shift config.toml")]
    assert out.getvalue() == f"RESULT {status if status != 'odd' else 'ERROR'}\n"
    assert err.getvalue() == ""


def test_e8_dry_run_never_opens_config_or_runs() -> None:
    calls: list[Path] = []
    out, err = StringIO(), StringIO()

    def run(path: Path) -> str:
        calls.append(path)
        return "PASS"

    assert main(["--dry-run", "--config", "absent.toml"], run, out, err) == 0
    assert calls == []
    assert out.getvalue() == f"DRY RUN {Path('absent.toml')}\n"
    assert err.getvalue() == ""


@pytest.mark.parametrize("argv", [[], ["--config"], ["--config", "x", "--bogus"], ["--dry-run"]])
def test_e8_usage_errors_do_not_run(argv: list[str]) -> None:
    calls: list[Path] = []
    out, err = StringIO(), StringIO()

    def run(path: Path) -> str:
        calls.append(path)
        return "PASS"

    assert main(argv, run, out, err) == 2
    assert calls == []
    assert out.getvalue() == ""
    assert "usage:" in err.getvalue() and "error:" in err.getvalue()


def test_e8_help_is_successful_without_config() -> None:
    calls: list[Path] = []
    out, err = StringIO(), StringIO()

    def run(path: Path) -> str:
        calls.append(path)
        return "PASS"

    assert main(["--help"], run, out, err) == 0
    assert calls == []
    assert "--config" in out.getvalue() and "--dry-run" in out.getvalue()
    assert err.getvalue() == ""


def test_e8_run_exception_returns_error() -> None:
    out, err = StringIO(), StringIO()

    def run(path: Path) -> str:
        raise OSError("config not readable")

    assert main(["--config", "missing.toml"], run, out, err) == 2
    assert out.getvalue() == "RESULT ERROR\n"
    assert err.getvalue() == ""


def test_e8_operator_interrupt_is_not_a_result() -> None:
    def run(path: Path) -> str:
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        main(["--config", "x.toml"], run, StringIO(), StringIO())


GOOD_SERVICE = """[Unit]
Description=Chassis station
[Service]
User=station
ExecStart=/opt/station/bin/run --serial %i
Restart=on-failure
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
"""


def test_e9_safe_service_and_literal_percent() -> None:
    assert service_findings(GOOD_SERVICE) == []


def test_e9_reports_all_missing_in_fixed_order() -> None:
    assert service_findings("[Unit]\nDescription=Station\n") == [
        "User", "ExecStart", "Restart", "NoNewPrivileges",
    ]
    assert service_findings("[Service]\n") == ["User", "ExecStart", "Restart", "NoNewPrivileges"]


@pytest.mark.parametrize("old,new,expected", [
    ("User=station", "User=root", "User"), ("User=station", "User=", "User"),
    ("ExecStart=/opt/station/bin/run --serial %i", "ExecStart=station", "ExecStart"),
    ("Restart=on-failure", "Restart=always", "Restart"),
    ("NoNewPrivileges=true", "NoNewPrivileges=false", "NoNewPrivileges"),
    ("User=station", "user=station", "User"),
])
def test_e9_detects_individual_policy_violation(old: str, new: str, expected: str) -> None:
    assert service_findings(GOOD_SERVICE.replace(old, new)) == [expected]


@pytest.mark.parametrize("text", [
    "[Service\nUser=station\n",
    "[Service]\nUser=station\nUser=root\n",
    "[Service]\nUser=station\n[Service]\n",
])
def test_e9_bad_syntax_is_not_a_policy_finding(text: str) -> None:
    with pytest.raises(ValueError):
        service_findings(text)


@pytest.mark.parametrize("status,age,expected", [
    (0x01, 0.5, []), (0x01, 1.0, []), (0x01, 1.001, ["STALE"]),
    (0x00, 0.0, ["DOOR_OPEN"]), (0x05, 0.0, ["ESTOP"]),
    (0x81, 0.0, ["SUPPLY_FAULT"]),
    (0x84, 2.0, ["DOOR_OPEN", "ESTOP", "SUPPLY_FAULT", "STALE"]),
])
def test_e10_hardware_bits_and_age(status: int, age: float, expected: list[str]) -> None:
    assert interlock_reasons(status, age, 1.0) == expected


def test_e10_ignores_unassigned_register_bits() -> None:
    assert interlock_reasons(0x7B, 0.0, 1.0) == []


@pytest.mark.parametrize("status", [-1, 256])
def test_e10_status_must_fit_a_byte(status: int) -> None:
    with pytest.raises(ValueError):
        interlock_reasons(status, 0.0, 1.0)


@pytest.mark.parametrize("age,maximum", [
    (-1.0, 1.0), (math.nan, 1.0), (math.inf, 1.0),
    (0.0, 0.0), (0.0, -1.0), (0.0, math.inf), (0.0, math.nan),
])
def test_e10_invalid_age_configuration(age: float, maximum: float) -> None:
    with pytest.raises(ValueError):
        interlock_reasons(1, age, maximum)
