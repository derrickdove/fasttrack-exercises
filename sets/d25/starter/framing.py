import socket


def frame(payload: bytes) -> bytes:
    """Prefix payload with its length as four unsigned big-endian bytes."""
    raise NotImplementedError("E1: encode the payload length and append the payload")


class FrameReader:
    """Keep unfinished bytes between feed calls; limit payloads to 1,000,000 bytes."""

    def __init__(self) -> None:
        """Start with no buffered bytes."""
        raise NotImplementedError("E2: initialize the unfinished-frame buffer")

    def feed(self, chunk: bytes) -> list[bytes]:
        """Return all complete payloads in order; retain any incomplete frame."""
        raise NotImplementedError("E2: buffer chunks and extract complete frames")


def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes; reject negative n and raise ConnectionError on EOF."""
    raise NotImplementedError("E3: loop until n bytes arrive or the peer closes")


def request(sock: socket.socket, payload: bytes) -> bytes:
    """Send one frame with sendall; read one reply, limited to 1,000,000 bytes."""
    raise NotImplementedError("E4: send the command frame and read exactly one reply")
