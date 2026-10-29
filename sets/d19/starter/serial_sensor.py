"""Read serial sensor measurements at a chassis test station."""

import serial  # type: ignore[import-untyped]


def open_loopback(timeout: float) -> serial.Serial:
    """Open loop:// with bounded read and write waits; caller closes it."""
    raise NotImplementedError("E1: open a pySerial loop:// port with the supplied timeout")


def send_line(port: serial.Serial, text: str) -> None:
    """Write ASCII text plus CRLF; reject text containing CR or LF."""
    raise NotImplementedError("E2: encode one ASCII command and append CRLF")


def read_line(port: serial.Serial) -> str:
    """Read one ASCII CRLF line; distinguish silence from a damaged line."""
    raise NotImplementedError("E2: read a line, check CRLF, and decode its payload")


def parse_sensor_line(line: str) -> dict[str, float]:
    """Check $payload*HH and convert comma-separated label/value pairs."""
    raise NotImplementedError("E3: verify the XOR checksum before parsing measurements")


def read_frames(port: serial.Serial, count: int) -> tuple[list[dict[str, float]], int]:
    """Collect count valid frames and count rejected lines; propagate timeouts."""
    raise NotImplementedError("E4: collect valid sensor frames while counting corrupted lines")


def bus_answers() -> dict[str, str]:
    """Return Q1 through Q5 mapped to uppercase option letters for the bus quiz."""
    raise NotImplementedError("E5: return the option letters for the bench bus questions")
