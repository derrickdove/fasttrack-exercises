"""Process helpers for a chassis test station."""
from __future__ import annotations

import signal
import subprocess
from types import FrameType, TracebackType


def run_tool(args: list[str], timeout: float) -> tuple[int, str, str]:
    """Capture a tool's code and text; return (-9, "", "timeout") on timeout."""
    raise NotImplementedError("E1: Run an argument list and capture both output streams")


def exit_code_meaning(code: int) -> str:
    """Describe success, failure, usage, signal termination, or another exit code."""
    raise NotImplementedError("E2: Translate the station tool's exit code")


class GracefulStop:
    """Record SIGINT/SIGTERM as requested=True while inside a with block."""

    requested: bool

    def __init__(self) -> None:
        raise NotImplementedError("E3: Initialize the stop-request flag")

    def __enter__(self) -> GracefulStop:
        raise NotImplementedError("E3: Reset the flag, save handlers, and install your handler")

    def _handle(self, signum: int, frame: FrameType | None) -> None:
        raise NotImplementedError("E3: Record a stop request without raising or exiting")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        raise NotImplementedError("E3: Restore saved signal handlers and let exceptions propagate")


def supervise(cmd: list[str], restarts: int) -> list[int]:
    """Run at most restarts+1 attempts with a five-second timeout each; stop on 0."""
    raise NotImplementedError("E4: Retry a failed station tool within the restart budget")
