"""A bench power supply with an injectable VISA resource manager."""
from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Literal, Protocol, runtime_checkable
import tomllib

import pyvisa


@runtime_checkable
class ResourceLike(Protocol):
    """Supplied: the text-resource operations this driver needs."""

    timeout: float
    read_termination: str | None
    write_termination: str | None

    def write(self, message: str, /) -> int: ...

    def read(self) -> str: ...

    def query(self, message: str, /) -> str: ...

    def close(self) -> None: ...


class ResourceManagerLike(Protocol):
    """Supplied: open a text resource by its VISA name."""

    def open_resource(self, resource_name: str) -> ResourceLike: ...


class Psu:
    """A single-output bench power supply using SCPI over TCP/IP."""

    def __init__(
        self,
        ip: str,
        timeout_ms: int = 2000,
        *,
        rm: ResourceManagerLike | pyvisa.ResourceManager | None = None,
        max_voltage: float | None = None,
        max_current: float | None = None,
    ) -> None:
        raise NotImplementedError("E5: validate timeout, open the resource and set communication attributes; E6: retain limits")

    def read_voltage(self) -> float:
        raise NotImplementedError("E5: query MEAS:VOLT? and convert the reply to float")

    def read_current(self) -> float:
        raise NotImplementedError("E5: query MEAS:CURR? and convert the reply to float")

    def set_voltage(self, volts: float) -> None:
        raise NotImplementedError("E5: reject negative volts and write three decimals; E6: enforce max_voltage")

    def set_current_limit(self, amps: float) -> None:
        raise NotImplementedError("E5: reject negative amps and write three decimals; E6: enforce max_current")

    def enable_output(self, enable: bool) -> None:
        raise NotImplementedError("E5: require a bool and write OUTP 1 or OUTP 0")

    @classmethod
    def from_config(
        cls, path: str | Path, *, rm: ResourceManagerLike | pyvisa.ResourceManager | None = None
    ) -> Psu:
        raise NotImplementedError("E6: load TOML, validate keys and construct cls with the supplied manager")

    def close(self) -> None:
        raise NotImplementedError("E6: close the resource at most once")

    def __enter__(self) -> Psu:
        raise NotImplementedError("E6: return this supply for the with block")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        raise NotImplementedError("E6: turn output off and always close, preserving a block exception")
