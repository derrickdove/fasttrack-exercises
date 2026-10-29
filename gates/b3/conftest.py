"""Gate-owned transports; load learner code only when a check runs."""

from collections import deque
from collections.abc import Callable, Iterator
from importlib import import_module
from types import ModuleType
import sys

import pytest


class FakeTransport:
    def __init__(self, replies: dict[str, list[str]] | None = None) -> None:
        self.replies = {cmd: deque(values) for cmd, values in (replies or {}).items()}
        self.events: list[tuple[str, str]] = []
        self.closed = False
        self.fail_first_off = False

    def write(self, cmd: str) -> None:
        self.events.append(("write", cmd))
        if self.fail_first_off and cmd == "OUTP OFF":
            self.fail_first_off = False
            raise OSError("output shutdown failed")

    def query(self, cmd: str) -> str:
        self.events.append(("query", cmd))
        assert cmd in self.replies and self.replies[cmd], f"unexpected query: {cmd}"
        return self.replies[cmd].popleft()

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def instruments() -> ModuleType:
    return import_module("chassis.instruments")


@pytest.fixture
def fake_factory() -> type[FakeTransport]:
    return FakeTransport


@pytest.fixture
def import_isolated_instruments() -> Iterator[Callable[[], ModuleType]]:
    """Let a check install its mock before any learner package code imports it."""
    saved = {name: module for name, module in sys.modules.copy().items()
             if name == "chassis" or name.startswith("chassis.")}
    for name in saved:
        del sys.modules[name]
    try:
        yield lambda: import_module("chassis.instruments")
    finally:
        for name in list(sys.modules):
            if name == "chassis" or name.startswith("chassis."):
                del sys.modules[name]
        sys.modules.update(saved)
