"""Exceptions and recovery for a test station's instrument calls."""
from collections.abc import Callable


class InstrumentTimeout(Exception):
    """An instrument did not answer in the time allowed."""

    message: str

    def __init__(self, message: str) -> None:
        """Store the timeout message and initialize Exception with it."""
        raise NotImplementedError("E1: Store the timeout message")

    def __str__(self) -> str:
        """Return the timeout message unchanged."""
        raise NotImplementedError("E1: Return the timeout message")


class InstrumentError(Exception):
    """An instrument reported an error code and a message."""

    code: int
    message: str

    def __init__(self, code: int, message: str) -> None:
        """Store code and message; initialize Exception with both arguments."""
        raise NotImplementedError("E1: Store the instrument error details")

    def __str__(self) -> str:
        """Return 'instrument error <code>: <message>'."""
        raise NotImplementedError("E1: Format the instrument error details")


def parse_error_reply(reply: str) -> tuple[int, str]:
    """Parse a signed decimal code and quoted message; reject malformed replies."""
    raise NotImplementedError("E2: Validate and parse one instrument error reply")


def drain_errors(
    query: Callable[[str], str], max_reads: int = 20
) -> list[tuple[int, str]]:
    """Read SYST:ERR? through code zero, returning only nonzero replies."""
    raise NotImplementedError("E3: Read errors until zero within the read budget")


def safe_measure(measure: Callable[[], float], retries: int) -> float:
    """Retry only timeouts, allowing retries extra calls after the first call."""
    raise NotImplementedError("E4: Retry timeouts and re-raise the last one")
