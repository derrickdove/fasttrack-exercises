from collections import deque
from collections.abc import Callable, Iterator
from queue import Queue
import socket
from threading import Thread

import pytest

from starter.framing import FrameReader, frame, recv_exact, request


def _wire(payload: bytes) -> bytes:
    """Build fixture bytes without depending on the learner's E1."""
    return len(payload).to_bytes(4, "big") + payload


class ScriptedSocket:
    """Socket stand-in that deterministically splits reads at supplied boundaries."""

    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = deque(chunks)
        self.read_sizes: list[int] = []
        self.sent: list[bytes] = []

    def recv(self, size: int) -> bytes:
        self.read_sizes.append(size)
        assert size > 0, "do not call recv for a zero-length payload"
        if not self.chunks:
            return b""
        chunk = self.chunks.popleft()
        result = chunk[:size]
        if len(chunk) > size:
            self.chunks.appendleft(chunk[size:])
        return result

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)


Station = Callable[[list[bytes]], tuple[socket.socket, Queue[bytes]]]


@pytest.fixture
def station() -> Iterator[Station]:
    """Serve one reply per command, sending each reply one byte at a time."""
    clients: list[socket.socket] = []
    listeners: list[socket.socket] = []
    workers: list[Thread] = []

    def start(replies: list[bytes]) -> tuple[socket.socket, Queue[bytes]]:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listeners.append(listener)
        listener.settimeout(2.0)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        received: Queue[bytes] = Queue()

        def read_bytes(connection: socket.socket, count: int) -> bytes | None:
            pending = bytearray()
            while len(pending) < count:
                chunk = connection.recv(count - len(pending))
                if not chunk:
                    return None
                pending.extend(chunk)
            return bytes(pending)

        def serve() -> None:
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2.0)
                    connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    for reply in replies:
                        header = read_bytes(connection, 4)
                        if header is None:
                            return  # A starter stub closes without sending a command.
                        command = read_bytes(connection, int.from_bytes(header, "big"))
                        if command is None:
                            return
                        received.put(command)
                        for byte in reply:
                            connection.sendall(bytes([byte]))
            except OSError:
                # A deliberately broken learner request may close early. Client-side
                # checks still detect missing/wrong replies and time out if needed.
                return

        client = socket.create_connection(listener.getsockname(), timeout=2.0)
        clients.append(client)
        worker = Thread(target=serve, name="d25-instrument")
        workers.append(worker)
        worker.start()
        return client, received

    yield start
    for client in clients:
        client.close()
    for worker in workers:
        worker.join(timeout=3.0)
    for listener in listeners:
        listener.close()
    assert all(not worker.is_alive() for worker in workers), "instrument thread did not stop"


@pytest.mark.parametrize("payload", [b"ID?", b"CH1:VOLT?", b""])
def test_e1_command_header(payload: bytes) -> None:
    expected = bytes([0, 0, 0, len(payload)]) + payload
    assert frame(payload) == expected, "prefix must count payload bytes, excluding the header"


def test_e1_binary_command() -> None:
    payload = b"\x00\xff\n\r"
    assert frame(payload) == b"\x00\x00\x00\x04" + payload, "binary command bytes must survive unchanged"


def test_e1_big_endian_length() -> None:
    payload = b"V" * 258
    assert frame(payload) == b"\x00\x00\x01\x02" + payload, "258 must encode as 00 00 01 02"


def test_e2_every_two_chunk_split() -> None:
    payloads = [b"CH1:12.5", b"", b"\x00\xffOK"]
    wire = b"".join(_wire(payload) for payload in payloads)
    for split in range(len(wire) + 1):
        reader = FrameReader()
        first = reader.feed(wire[:split])
        second = reader.feed(wire[split:])
        assert first + second == payloads, f"lost, duplicated, or reordered payloads at split {split}"
        assert reader.feed(b"") == [], "completed frames must not be returned again"


def test_e2_bytewise_header_and_payload() -> None:
    reader = FrameReader()
    wire = _wire(b"READY")
    for index, byte in enumerate(wire):
        expected = [b"READY"] if index == len(wire) - 1 else []
        assert reader.feed(bytes([byte])) == expected, f"reply completed at wrong byte {index}"


def test_e2_complete_frames_before_incomplete_tail() -> None:
    reader = FrameReader()
    assert reader.feed(_wire(b"OK") + _wire(b"") + _wire(b"FAULT")[:-2]) == [b"OK", b""], "return complete frames immediately"
    assert reader.feed(b"") == [], "empty input must preserve an incomplete payload"
    assert reader.feed(b"LT") == [b"FAULT"], "retain the unfinished payload across calls"
    assert reader.feed(b"") == [], "completed reply should be removed from the buffer"


def test_e2_independent_readers() -> None:
    first, second = FrameReader(), FrameReader()
    assert first.feed(_wire(b"CH1")[:-1]) == []
    assert second.feed(_wire(b"CH2")) == [b"CH2"], "reader instances must not share pending bytes"
    assert first.feed(b"1") == [b"CH1"]


def test_e2_exact_size_limit() -> None:
    reader = FrameReader()
    payload = b"T" * 1_000_000
    assert reader.feed(_wire(payload)) == [payload], "exactly 1,000,000 payload bytes are allowed"


@pytest.mark.parametrize("size", [1_000_001, 0xFFFFFFFF])
def test_e2_reject_oversized_header_without_body(size: int) -> None:
    reader = FrameReader()
    header = size.to_bytes(4, "big")
    assert reader.feed(header[:3]) == [], "three header bytes are not enough to know the length"
    with pytest.raises(ValueError):
        reader.feed(header[3:])


def test_e3_partial_reads_and_next_reply() -> None:
    sock = ScriptedSocket([b"O", b"K!NEXT"])
    assert recv_exact(sock, 3) == b"OK!", "collect all partial reads before returning"
    assert sock.read_sizes == [3, 2], "ask only for the number of bytes still missing"
    assert sock.recv(4) == b"NEXT", "do not consume bytes belonging to the next reply"


@pytest.mark.parametrize("chunks", [[], [b"O"]])
def test_e3_eof_is_connection_error(chunks: list[bytes]) -> None:
    with pytest.raises(ConnectionError):
        recv_exact(ScriptedSocket(chunks), 2)


def test_e3_zero_and_negative_count() -> None:
    sock = ScriptedSocket([b"READY"])
    assert recv_exact(sock, 0) == b"", "zero bytes need no socket operation"
    with pytest.raises(ValueError):
        recv_exact(sock, -1)
    assert sock.read_sizes == [], "zero/negative sizes must not read from the socket"


def test_e3_socket_error_propagates() -> None:
    class TimedOutSocket:
        def recv(self, size: int) -> bytes:
            raise TimeoutError("instrument did not reply")

    with pytest.raises(TimeoutError, match="instrument did not reply"):
        recv_exact(TimedOutSocket(), 1)


def test_e4_scripted_fragments_and_sendall() -> None:
    wire = _wire(b"\x00\xffOK")
    sock = ScriptedSocket([bytes([byte]) for byte in wire])
    assert request(sock, b"MEAS?") == b"\x00\xffOK", "decode fragmented reply header and payload"
    assert sock.sent == [_wire(b"MEAS?")], "send exactly one complete command frame via sendall"


@pytest.mark.parametrize("command,reply", [(b"STATUS?", b"READY"), (b"", b""), (b"RAW?", b"\x00\xff\n")])
def test_e4_threaded_station(station: Station, command: bytes, reply: bytes) -> None:
    sock, received = station([_wire(reply)])
    before = sock.gettimeout()
    assert request(sock, command) == reply, "return the local instrument's payload without its header"
    assert received.get(timeout=2.0) == command, "instrument must receive the unchanged command"
    assert sock.fileno() != -1, "request must leave the caller's socket open"
    assert sock.gettimeout() == before, "request must preserve the caller's timeout"


def test_e4_repeated_commands_on_one_connection(station: Station) -> None:
    sock, received = station([_wire(b"READY"), _wire(b"12.5")])
    assert request(sock, b"STATUS?") == b"READY"
    assert request(sock, b"CH1?") == b"12.5", "reuse the same connection for another command"
    assert [received.get(timeout=2.0), received.get(timeout=2.0)] == [b"STATUS?", b"CH1?"]


def test_e4_leaves_following_frame_unread() -> None:
    sock = ScriptedSocket([_wire(b"OK") + _wire(b"ALARM")])
    assert request(sock, b"ARM") == b"OK", "return only the first reply"
    assert sock.recv(100) == _wire(b"ALARM"), "leave following frame bytes available to the caller"


@pytest.mark.parametrize("wire", [b"", b"\x00\x00", b"\x00\x00\x00\x03O"])
def test_e4_threaded_early_close(station: Station, wire: bytes) -> None:
    sock, received = station([wire])
    with pytest.raises(ConnectionError):
        request(sock, b"STATUS?")
    assert received.get(timeout=2.0) == b"STATUS?"


def test_e4_reject_oversized_reply_before_reading_body(station: Station) -> None:
    sock, _ = station([(1_000_001).to_bytes(4, "big")])
    with pytest.raises(ValueError):
        request(sock, b"TRACE?")
