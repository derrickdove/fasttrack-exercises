"""UDP helpers for a local chassis test station."""

import socket


def make_receiver(
    host: str = "127.0.0.1", port: int = 0, timeout: float = 0.5
) -> socket.socket:
    """Return an open, bound IPv4 UDP socket with the requested timeout."""
    raise NotImplementedError("E1: Create, bind, and set a timeout on a UDP socket.")


def send_datagram(data: bytes, addr: tuple[str, int]) -> None:
    """Send one unchanged datagram using a temporary socket; always close it."""
    raise NotImplementedError("E2: Send one bytes payload with a temporary UDP socket.")


def receive_all(
    sock: socket.socket, max_packets: int, idle_timeout: float
) -> list[bytes]:
    """Collect up to max_packets; stop on idle and restore the original timeout."""
    raise NotImplementedError("E3: Collect datagrams until the count or idle limit.")


def echo_once(sock: socket.socket) -> tuple[str, int]:
    """Reply to one sender with uppercase bytes using the caller's socket."""
    raise NotImplementedError("E4: Receive one datagram and send an uppercase reply.")
