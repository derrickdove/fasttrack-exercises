"""Read an offline test-station capture; see README.md for byte layouts."""
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO


def read_global_header(f: BinaryIO) -> dict[str, int | str]:
    """Read 24 bytes at the current position; return capture format settings."""
    raise NotImplementedError("E1: decode the global header in its declared byte order")


def iter_records(path: str | Path) -> Iterator[tuple[float, bytes]]:
    """Yield capture timestamps in seconds and stored frames, in file order."""
    raise NotImplementedError("E2: read record headers and their captured frame bytes")


def udp_payloads(path: str | Path, port: int) -> list[bytes]:
    """Return complete UDP payloads addressed to port from an Ethernet capture."""
    raise NotImplementedError("E3: follow Ethernet, IPv4 IHL, and UDP lengths")


def telemetry_from_capture(path: str | Path, port: int) -> list[tuple[int, int]]:
    """Return (sequence, channel count) for structurally valid, CRC-valid packets."""
    raise NotImplementedError("E4: validate telemetry structure and CRC before summarizing")
