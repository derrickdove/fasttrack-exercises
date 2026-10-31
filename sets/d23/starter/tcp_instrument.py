"""A newline-delimited connection to a station instrument."""
from __future__ import annotations

import socket
from types import TracebackType


class TcpInstrument:
    """Own one TCP socket and preserve unread reply bytes between queries."""

    def __init__(self, host: str, port: int, timeout: float = 2.0) -> None:
        """Connect with create_connection and apply timeout to socket operations."""
        raise NotImplementedError("E1: Connect to the instrument with a timeout")

    def close(self) -> None:
        """Close the socket; calling close again is harmless."""
        raise NotImplementedError("E1: Release the instrument socket")

    def __enter__(self) -> TcpInstrument:
        """Return this connected instrument for a with block."""
        raise NotImplementedError("E1: Return this instrument")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close on exit and let any exception continue to the caller."""
        raise NotImplementedError("E1: Close when leaving the with block")

    def write(self, cmd: str) -> None:
        """Send UTF-8 cmd plus LF, without reading; name cmd on timeout."""
        raise NotImplementedError("E2: Send the complete newline-terminated command")

    def query(self, cmd: str) -> str:
        """Send cmd and read one LF-terminated reply; preserve extra bytes."""
        raise NotImplementedError("E2: Collect bytes through one reply newline")

    def query_many(self, cmds: list[str]) -> list[str]:
        """Send each query and read its complete reply before sending the next."""
        raise NotImplementedError("E4: Query each command and collect its reply before the next")

