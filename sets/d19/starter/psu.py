"""A bench power supply with an injectable VISA resource manager."""
from __future__ import annotations

from math import isfinite
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
        # Supplied: validate and retain limits before any connection is opened.
        for key, maximum in (("max_voltage", max_voltage), ("max_current", max_current)):
            if maximum is not None and (not isfinite(maximum) or maximum < 0):
                raise ValueError(f"{key} must be finite and nonnegative")
        self._max_voltage = max_voltage
        self._max_current = max_current
        self._closed = False
        # E5: replace the raise below; keep the supplied setup above.
        raise NotImplementedError("E5: validate timeout, open the resource and set communication attributes")

    def read_voltage(self) -> float:
        raise NotImplementedError("E5: query MEAS:VOLT? and convert the reply to float")

    def read_current(self) -> float:
        raise NotImplementedError("E5: query MEAS:CURR? and convert the reply to float")

    def set_voltage(self, volts: float) -> None:
        raise NotImplementedError("E5: reject negative or non-finite volts and write three decimals; E6: enforce max_voltage")

    def set_current_limit(self, amps: float) -> None:
        raise NotImplementedError("E5: reject negative or non-finite amps and write three decimals; E6: enforce max_current")

    def enable_output(self, enable: bool) -> None:
        raise NotImplementedError("E5: require a bool and write OUTP 1 or OUTP 0")

    @classmethod
    def from_config(
        cls, path: str | Path, *, rm: ResourceManagerLike | pyvisa.ResourceManager | None = None
    ) -> Psu:
        """Supplied: validate TOML settings before constructing the requested class."""
        with open(path, "rb") as source:
            config = tomllib.load(source)
        ip = config.get("ip")
        if not isinstance(ip, str):
            raise ValueError("ip must be a str")
        timeout_ms = config.get("timeout_ms", 2000)
        if type(timeout_ms) is not int or timeout_ms <= 0:
            raise ValueError("timeout_ms must be a positive int")
        for key in ("max_voltage", "max_current"):
            if key in config:
                maximum = config[key]
                if isinstance(maximum, bool) or not isinstance(maximum, (int, float)):
                    raise ValueError(f"{key} must be a number")
                if not isfinite(maximum) or maximum < 0:
                    raise ValueError(f"{key} must be finite and nonnegative")
        return cls(
            ip, timeout_ms, rm=rm,
            max_voltage=config.get("max_voltage"),
            max_current=config.get("max_current"),
        )

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
