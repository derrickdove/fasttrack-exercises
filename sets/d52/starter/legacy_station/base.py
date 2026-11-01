"""Shared instrument interface; transports own all actual waiting."""

from abc import ABC, abstractmethod
import math
from typing import Protocol


class Transport(Protocol):
    """The station accepts any object with these two communication methods.

    Commands have no trailing newline. A real transport supplies framing,
    applies the timeout, and raises TimeoutError if the instrument is silent.
    Tests use an in-memory replacement, so nothing here talks to hardware.
    """

    def write(self, command: str, timeout_s: float) -> None:
        """Send a command with a finite wait for completion."""
        ...

    def query(self, command: str, timeout_s: float) -> str:
        """Send a command and return its reply within the timeout."""
        ...


class Driver(ABC):
    """Base class for instruments that expose one numeric measurement.

    Each instance owns its transport and a timeout in seconds. Subclasses
    supply read(); shared methods forward the timeout without retrying.
    """

    def __init__(self, transport: Transport, timeout_s: float = 0.4) -> None:
        """Reject an unusable timeout before any communication occurs."""
        if not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("timeout_s must be finite and positive")
        self.transport = transport
        self.timeout_s = timeout_s

    def _write(self, command: str) -> None:
        """Forward one write, including this driver's configured timeout."""
        self.transport.write(command, self.timeout_s)

    def _query(self, command: str) -> str:
        """Forward one query, including this driver's configured timeout."""
        return self.transport.query(command, self.timeout_s)

    def identify(self) -> str:
        """Return the instrument identification without surrounding whitespace."""
        return self._query("*IDN?").strip()

    @abstractmethod
    def read(self) -> float:
        """Return the instrument's primary measurement in its documented unit."""
        raise TypeError("A concrete driver must implement read")
