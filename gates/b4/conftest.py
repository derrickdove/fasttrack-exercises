"""Gate-owned wire examples and cleanup; learner imports happen at test time."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from importlib import import_module
import socket
import struct
import threading
from types import ModuleType
from typing import Any
import zlib

import pytest


@pytest.fixture
def telemetry() -> ModuleType:
    return import_module("chassis.telemetry")


@pytest.fixture
def wire_packet() -> Callable[..., bytes]:
    def pack(
        seq: int = 7, timestamp_us: int = 123456789,
        readings: tuple[tuple[int, float], ...] = ((3, 24.125),), *,
        sync: int = 0xEB90, count: int | None = None,
    ) -> bytes:
        body = struct.pack(">HHQB", sync, seq, timestamp_us,
                           len(readings) if count is None else count)
        body += b"".join(struct.pack(">Bf", channel, value) for channel, value in readings)
        return body + struct.pack(">I", zlib.crc32(body))

    return pack


@pytest.fixture
def send_datagram() -> Iterator[Callable[[int, bytes], None]]:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.bind(("127.0.0.1", 0))
        sender.settimeout(1.0)

        def send(port: int, data: bytes) -> None:
            sender.sendto(data, ("127.0.0.1", port))

        yield send


@pytest.fixture
def listener_factory(telemetry: ModuleType) -> Callable[..., Any]:
    @contextmanager
    def create(on_packet: Callable[..., None], **kwargs: Any) -> Iterator[Any]:
        listener = telemetry.TelemetryListener("127.0.0.1", 0, on_packet, **kwargs)
        try:
            yield listener
        finally:
            listener.stop()

    return create


@pytest.fixture(autouse=True)
def join_listener_threads() -> Iterator[None]:
    original_threads = set(threading.enumerate())
    yield
    # Observe standard Thread objects, never learner-private attributes.
    threads = set(threading.enumerate()) - original_threads
    for thread in threads:
        thread.join(timeout=2.0)
    assert not any(thread.is_alive() for thread in threads), "listener leaked a thread"
