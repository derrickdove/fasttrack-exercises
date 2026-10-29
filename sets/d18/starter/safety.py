"""Safety helpers for a test station; replace the E1-E4 stub bodies."""
from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from functools import wraps
from types import TracebackType
from typing import Literal, ParamSpec, Protocol, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


class OutputDevice(Protocol):
    """Supplied typing interface: any object with this method is accepted."""

    def output(self, ch: int, on: bool) -> None: ...


class VoltageDevice(OutputDevice, Protocol):
    """Supplied typing interface for a voltage-setting power supply."""

    def set_voltage(self, ch: int, voltage: float) -> None: ...


class OutputGuard:
    """E1: switch every listed channel off when leaving a with block."""

    def __init__(self, psu: OutputDevice, channels: Sequence[int]) -> None:
        raise NotImplementedError("E1: store the supply and a snapshot of its channels")

    def __enter__(self) -> OutputGuard:
        raise NotImplementedError("E1: return this guard without changing outputs")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        raise NotImplementedError("E1: attempt every output-off call and preserve the original error")


def retry(
    times: int,
    exceptions: tuple[type[Exception], ...],
    delay_s: float = 0,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """E2: decorate a station operation with a limited number of attempts."""
    raise NotImplementedError("E2: retry only listed errors and sleep only between attempts")


def with_deadline(
    fn: Callable[[], T],
    timeout_s: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """E3: poll immediately, then every 0.01 s, until success or timeout."""
    raise NotImplementedError("E3: use an injected clock and sleep to bound repeated checks")


def ramp_voltage(
    psu: VoltageDevice,
    ch: int,
    target: float,
    step: float,
    settle: Callable[[], None],
) -> None:
    """E4: ramp from an already enabled 0 V output; recover safely on error."""
    raise NotImplementedError("E4: step up without overshoot; reset and disable on failure")
