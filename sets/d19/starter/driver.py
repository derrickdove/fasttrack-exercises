"""Instrument drivers that accept a replaceable text transport."""
from typing import Protocol


class Transport(Protocol):
    """Supplied interface: send a command or send a query and return its reply."""

    def write(self, command: str) -> None:
        raise NotImplementedError("E1: interface only; implement FakeTransport.write")

    def query(self, command: str) -> str:
        raise NotImplementedError("E1: interface only; implement FakeTransport.query")


class FakeTransport:
    """A scripted transport for checking drivers without connected hardware."""

    def __init__(self, replies: dict[str, str]) -> None:
        raise NotImplementedError("E1: store scripted replies and create an empty writes list")

    def write(self, command: str) -> None:
        raise NotImplementedError("E1: append the exact command to writes")

    def query(self, command: str) -> str:
        raise NotImplementedError("E1: return the scripted reply or raise KeyError")


class Dmm:
    """A digital multimeter using the supplied transport."""

    def __init__(self, transport: Transport) -> None:
        raise NotImplementedError("E2: retain the supplied transport without sending commands")

    def idn(self) -> str:
        raise NotImplementedError("E2: query *IDN? and strip surrounding whitespace")

    def measure_dc_voltage(self) -> float:
        raise NotImplementedError("E2: query MEAS:VOLT:DC? and convert the reply to float")


class PowerSupply:
    """A three-channel supply using the supplied transport."""

    def __init__(self, transport: Transport) -> None:
        raise NotImplementedError("E3: retain the supplied transport without sending commands")

    def set_voltage(self, ch: int, v: float) -> None:
        raise NotImplementedError("E3: validate both values before selecting and setting voltage")

    def output(self, ch: int, on: bool) -> None:
        raise NotImplementedError("E4: validate the channel, select it, then set output ON or OFF")

    def measure_voltage(self, ch: int) -> float:
        raise NotImplementedError("E4: validate and select the channel, then query MEAS:VOLT?")
