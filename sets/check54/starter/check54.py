"""Final station checks: independent, offline maintenance tasks."""
from __future__ import annotations

import argparse
import configparser
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct
from types import TracebackType
from typing import Callable, Protocol, TextIO

from pyvisa.constants import StatusCode
from pyvisa.errors import VisaIOError


@dataclass(frozen=True)
class StationConfig:
    station: str
    timeout_s: float
    retries: int
    channels: tuple[str, ...]


@dataclass(frozen=True)
class Snapshot:
    sequence: int
    voltage_v: float
    output_on: bool
    overtemp: bool


class Transport(Protocol):
    """Supplied interface; a real adapter is responsible for enforcing timeout_s."""

    def query(self, command: str, timeout_s: float) -> str:
        """Send a command and return its reply, or raise a transport error."""
        raise NotImplementedError("E2: implement query")

    def write(self, command: str) -> None:
        """Send a command that has no reply."""
        raise NotImplementedError("E2: implement write")

    def close(self) -> None:
        """Release the instrument connection."""
        raise NotImplementedError("E2: implement close")


class ResourceLike(Protocol):
    """Supplied VISA resource interface; timeout is in milliseconds."""

    timeout: int
    read_termination: str
    write_termination: str

    def write(self, cmd: str) -> None:
        """Send a command with no reply."""
        ...

    def query(self, cmd: str) -> str:
        """Return a reply; timeouts raise VisaTimeout or VisaIOError(error_timeout)."""
        ...

    def close(self) -> None:
        """Release the instrument connection."""
        ...


class ResourceManagerLike(Protocol):
    """Supplied interface for opening a VISA resource by name."""

    def open_resource(self, name: str) -> ResourceLike:
        ...


class OutputSupply(Protocol):
    """Supplied E10 interface; compatible with StationSupply or a recording fake."""

    def enable_output(self, on: bool) -> None:
        """Enable or disable the supply output."""
        ...


class VisaTimeout(Exception):
    """Supplied fake-resource timeout; real VISA uses VisaIOError(error_timeout)."""


def validate_config(raw: dict[str, object]) -> StationConfig:
    """E1: Validate the complete configuration before any instrument access."""
    raise NotImplementedError("E1: implement validate_config")


class StationSupply:
    """E2: Drive a supply using validated station settings."""

    # Supplied scaffolding: validate configuration and prepare the resource.
    def __init__(self, resource: ResourceLike, max_voltage: float) -> None:
        """Store an already-configured resource; callers use from_config."""
        self.resource = resource
        self.max_voltage = max_voltage
        self._closed = False

    @classmethod
    def from_config(
        cls, config: dict[str, object], rm: ResourceManagerLike,
    ) -> StationSupply:
        """Validate all settings, open the resource, and set its timeout/terminations."""
        for key in config:
            if key not in {"ip", "timeout_ms", "max_voltage"}:
                raise ValueError(f"unknown key: {key}")
        ip = config.get("ip")
        timeout_ms = config.get("timeout_ms", 2000)
        max_voltage = config.get("max_voltage")
        if not isinstance(ip, str) or not ip:
            raise ValueError("ip must be nonempty text")
        if type(timeout_ms) is not int or timeout_ms <= 0:
            raise ValueError("timeout_ms must be a positive integer")
        if (isinstance(max_voltage, bool)
                or not isinstance(max_voltage, (int, float))
                or not math.isfinite(max_voltage) or max_voltage <= 0):
            raise ValueError("max_voltage must be a positive finite number")
        resource = rm.open_resource(f"TCPIP::{ip}::INSTR")
        try:
            resource.timeout = timeout_ms
            resource.read_termination = "\n"
            resource.write_termination = "\n"
        except BaseException:
            try:
                resource.close()
            except BaseException:
                # A cleanup failure must not replace the setup exception.
                pass
            raise
        return cls(resource, max_voltage)

    # Learner work: implement the methods below.
    def read_voltage(self) -> float:
        """Query MEAS:VOLT?, retry one fake or VISA timeout, and convert the reply."""
        raise NotImplementedError("E2: query voltage with one timeout retry")

    def set_voltage(self, volts: float) -> None:
        """Require a finite value whose three-decimal command is within the limit."""
        raise NotImplementedError("E2: validate voltage before writing")

    def enable_output(self, on: bool) -> None:
        """Require exactly a bool, then write OUTP 1 or OUTP 0."""
        raise NotImplementedError("E2: check the output flag at runtime")

    def __enter__(self) -> StationSupply:
        """Return this supply for use in a with block."""
        raise NotImplementedError("E2: enter the supply context")

    def __exit__(
        self, exc_type: type[BaseException] | None,
        exc_value: BaseException | None, traceback: TracebackType | None,
    ) -> None:
        """Disable output and close, preserving any exception from the block."""
        raise NotImplementedError("E2: disable and always close on context exit")

    def close(self) -> None:
        """Close the resource at most once."""
        raise NotImplementedError("E2: make close idempotent")


def judge_samples(samples: list[float], low: float, high: float, required: int) -> str:
    """E3: Return ERROR, INCOMPLETE, FAIL or PASS using documented precedence."""
    raise NotImplementedError("E3: implement judge_samples")


def decode_snapshot(packet: bytes) -> Snapshot:
    """E4: Decode the eight-byte FC maintenance snapshot, checking its XOR."""
    # Supplied: reject the wrong length and unpack the wire fields.
    if len(packet) != 8:
        raise ValueError("snapshot must be eight bytes")
    magic, sequence, millivolts, flags, received = struct.unpack(">2sHHBB", packet)
    # Learner work: check the identifier, checksum and flags; build the Snapshot.
    raise NotImplementedError("E4: validate unpacked fields and return a Snapshot")


def audit_sequences(sequences: list[int]) -> dict[str, int]:
    """E5: Count accepted snapshots, missing numbers, duplicates and stale packets."""
    raise NotImplementedError("E5: implement audit_sequences")


def execute_steps(
    steps: list[tuple[str, Callable[[], str]]], cleanup: Callable[[], None]
) -> list[tuple[str, str]]:
    """E6: Stop calling steps after a failure; always run cleanup once."""
    raise NotImplementedError("E6: implement execute_steps")


def write_run_report(
    path: Path, station: str, rows: list[tuple[str, str]],
    requirement_steps: dict[str, list[str]],
) -> None:
    """E7: Save step evidence and an aggregate status for every requirement."""
    raise NotImplementedError("E7: implement write_run_report")


def main(
    argv: list[str], run: Callable[[Path], str], out: TextIO, err: TextIO,
) -> int:
    """E8: Parse an operator command and return its process exit code."""
    raise NotImplementedError("E8: implement main")


def service_findings(text: str) -> list[str]:
    """E9: Check four safety settings in an offline Linux service file."""
    raise NotImplementedError("E9: implement service_findings")


def interlock_reasons(status: int, telemetry_age_s: float, max_age_s: float) -> list[str]:
    """E10: Decode hardware inhibit bits and reject stale telemetry."""
    raise NotImplementedError("E10: implement interlock_reasons")


def run_interlocked(
    supply: OutputSupply, read_interlock: Callable[[], tuple[int, float]],
    max_age_s: float,
) -> list[str]:
    """E10: Read one interlock sample and enable only when no reasons inhibit it."""
    # Learner work: repair this ordering before running real hardware.
    supply.enable_output(True)
    status, age_s = read_interlock()
    reasons = interlock_reasons(status, age_s, max_age_s)
    return reasons
