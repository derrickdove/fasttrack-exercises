"""Loopback station tests: no instrument, internet, or fixed port required."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from io import BytesIO
import socket
from threading import Event, Thread
from unittest.mock import Mock

import pytest

from starter.tcp_instrument import TcpInstrument


class FakeInstrument:
    """Accept one station client and run a bounded instrument script."""

    def __init__(self, script: Callable[[socket.socket], None]) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(0.05)
        self.host, self.port = self.listener.getsockname()
        self.script = script
        self.client: socket.socket | None = None
        self.stopping = Event()
        self.errors: list[BaseException] = []
        self.thread = Thread(target=self._run, name="d20-fake-instrument", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        try:
            while not self.stopping.is_set():
                try:
                    client, _ = self.listener.accept()
                except TimeoutError:
                    continue
                self.client = client
                with client:
                    client.settimeout(1.5)
                    self.script(client)
                return
        except OSError as error:
            if not self.stopping.is_set():
                self.errors.append(error)
        except BaseException as error:
            self.errors.append(error)

    def stop(self) -> None:
        self.stopping.set()
        if self.client is not None:
            try:
                self.client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # The handler may already have closed the accepted socket.
        self.listener.close()
        self.thread.join(timeout=2.0)
        assert not self.thread.is_alive(), "fake instrument thread did not stop"
        assert not self.errors, f"fake instrument script failed: {self.errors!r}"


@pytest.fixture
def instrument_server() -> Iterator[Callable[[Callable[[socket.socket], None]], FakeInstrument]]:
    servers: list[FakeInstrument] = []

    def start(script: Callable[[socket.socket], None]) -> FakeInstrument:
        server = FakeInstrument(script)
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.stop()


def read_command(connection: socket.socket) -> bytes:
    """Read an exact command including its LF, without consuming the next one."""
    command = b""
    while not command.endswith(b"\n"):
        chunk = connection.recv(1)
        if not chunk:
            raise AssertionError(f"client closed before command newline: {command!r}")
        command += chunk
    return command


def observe_close(closed: Event) -> Callable[[socket.socket], None]:
    def script(connection: socket.socket) -> None:
        assert connection.recv(1) == b"", "closing a client must not send a command"
        closed.set()
    return script


class SocketView:
    """Keep real TCP but force small receives or a deterministic send timeout."""

    def __init__(self, connection: socket.socket, *, fail_send: bool = False) -> None:
        self.connection = connection
        self.fail_send = fail_send
        self.receive_calls = 0

    def __getattr__(self, name: str):
        return getattr(self.connection, name)

    def recv(self, size: int) -> bytes:
        self.receive_calls += 1
        return self.connection.recv(min(size, 2))

    def sendall(self, payload: bytes) -> None:
        if self.fail_send:
            raise TimeoutError("simulated full transmit buffer")
        self.connection.sendall(payload)


@pytest.mark.parametrize("timeout", [None, 0.35])
def test_e1_connects_with_timeout_and_closes(instrument_server, monkeypatch, timeout) -> None:
    closed = Event()
    server = instrument_server(observe_close(closed))
    original = socket.create_connection
    connections: list[socket.socket] = []
    calls = []

    def connect(address, timeout=None):
        calls.append((address, timeout))
        connection = original(address, timeout=timeout)
        connections.append(connection)
        return connection

    monkeypatch.setattr(socket, "create_connection", connect)
    client = (TcpInstrument(server.host, server.port) if timeout is None
              else TcpInstrument(server.host, server.port, timeout=timeout))
    try:
        expected_timeout = 2.0 if timeout is None else timeout
        assert calls == [((server.host, server.port), expected_timeout)], "use create_connection with the requested timeout"
        assert connections[0].gettimeout() == expected_timeout, "reads and writes need the same timeout"
    finally:
        client.close()
    client.close()
    assert closed.wait(1.0), "close() must release the station's TCP connection"


def test_e1_context_returns_self_and_closes(instrument_server) -> None:
    closed = Event()
    server = instrument_server(observe_close(closed))
    client = TcpInstrument(server.host, server.port)
    try:
        with client as entered:
            assert entered is client, "with must yield the connected instrument"
        assert closed.wait(1.0), "leaving with must close the connection"
    finally:
        client.close()


def test_e1_context_preserves_operator_error(instrument_server) -> None:
    closed = Event()
    server = instrument_server(observe_close(closed))
    with pytest.raises(ValueError, match="operator cancelled"):
        with TcpInstrument(server.host, server.port):
            raise ValueError("operator cancelled")
    assert closed.wait(1.0), "with must also close after a test-step exception"


@pytest.mark.parametrize("cmd", ["*RST", "OUTP ON", "DISP:TEXT café"])
def test_e2_write_sends_exact_bytes_without_reading(instrument_server, cmd) -> None:
    received: list[bytes] = []
    done = Event()

    def script(connection: socket.socket) -> None:
        received.append(read_command(connection))
        done.set()  # Deliberately send no reply to a write-only command.
        assert connection.recv(1) == b"", "write must send exactly one command line"

    server = instrument_server(script)
    with TcpInstrument(server.host, server.port, timeout=0.2) as client:
        assert client.write(cmd) is None, "write has no return value"
        assert done.wait(1.0), "instrument never received the command"
    assert received == [(cmd + "\n").encode("utf-8")], "append one LF and encode the command"


@pytest.mark.parametrize("reply", [b"  12.50 V  \n", b"\n", "Température OK\n".encode("utf-8")])
def test_e2_query_returns_only_reply_text(instrument_server, reply) -> None:
    def script(connection: socket.socket) -> None:
        assert read_command(connection) == b"MEAS:VOLT?\n"
        connection.sendall(reply)

    server = instrument_server(script)
    with TcpInstrument(server.host, server.port) as client:
        got = client.query("MEAS:VOLT?")
    assert got == reply[:-1].decode("utf-8"), "remove only LF; preserve spaces and allow an empty reply"


def test_e2_query_handles_several_receives(instrument_server, monkeypatch) -> None:
    reply = "BENCH,LOAD,Température-OK,1.0"

    def script(connection: socket.socket) -> None:
        assert read_command(connection) == b"*IDN?\n"
        connection.sendall((reply + "\n").encode("utf-8"))

    server = instrument_server(script)
    original = socket.create_connection
    views: list[SocketView] = []

    def connect(address, timeout=None):
        view = SocketView(original(address, timeout=timeout))
        views.append(view)
        return view

    monkeypatch.setattr(socket, "create_connection", connect)
    with TcpInstrument(server.host, server.port) as client:
        got = client.query("*IDN?")
    assert got == reply, "one recv is not one reply; decode after collecting the complete line"


def test_e2_query_preserves_buffered_reply_between_calls(monkeypatch) -> None:
    replies = BytesIO(b"first\nsecond\n")
    connection = Mock(spec=socket.socket)
    # Share one byte stream for direct recv and buffered socket readers.
    connection.recv.side_effect = replies.read
    connection.makefile.return_value = replies
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: connection)

    with TcpInstrument("127.0.0.1", 0) as client:
        assert client.query("FIRST?") == "first", "return only the first complete reply"
        assert client.query("SECOND?") == "second", "keep the next reply across query calls"


def test_e2_query_reports_closed_connection(instrument_server) -> None:
    def script(connection: socket.socket) -> None:
        assert read_command(connection) == b"READ?\n"
        connection.sendall(b"unfinished")  # Closing without LF is not a valid reply.

    server = instrument_server(script)
    with TcpInstrument(server.host, server.port) as client:
        with pytest.raises(ConnectionError):
            client.query("READ?")


@pytest.mark.parametrize("cmd,partial", [
    ("MEAS:CURR?", b""),
    ("FETCH:VOLT?", b"12.3"),
    (r'DISP:TEXT "C:\station\log"', b""),
    ('DISP:TEXT "station\tlog"', b"12.3"),
])
def test_e3_read_timeout_names_command(instrument_server, cmd, partial) -> None:
    def script(connection: socket.socket) -> None:
        assert read_command(connection) == (cmd + "\n").encode("utf-8")
        if partial:
            connection.sendall(partial)
        connection.recv(1)  # Wait for the client to close; no timing sleeps.

    server = instrument_server(script)
    with TcpInstrument(server.host, server.port, timeout=0.1) as client:
        with pytest.raises(TimeoutError) as failure:
            client.query(cmd)
        assert cmd in str(failure.value), "the operator needs the command that timed out"


@pytest.mark.parametrize("operation", ["write", "query"])
@pytest.mark.parametrize("cmd", ["OUTP OFF", r'DISP:TEXT "C:\station\log"', 'DISP:TEXT "station\tlog"'])
def test_e3_send_timeout_names_command(instrument_server, monkeypatch, operation, cmd) -> None:
    closed = Event()
    server = instrument_server(observe_close(closed))
    original = socket.create_connection

    def connect(address, timeout=None):
        return SocketView(original(address, timeout=timeout), fail_send=True)

    monkeypatch.setattr(socket, "create_connection", connect)
    with TcpInstrument(server.host, server.port) as client:
        with pytest.raises(TimeoutError) as failure:
            getattr(client, operation)(cmd)
        assert cmd in str(failure.value), "send timeouts also need command context"


def test_e4_pipeline_sends_every_command_before_reading(instrument_server) -> None:
    commands = ["MEAS:VOLT?", "MEAS:CURR?", "*OPC?"]

    def script(connection: socket.socket) -> None:
        for cmd in commands:
            assert read_command(connection) == (cmd + "\n").encode("utf-8")
        # One combined transmission exercises preservation of later reply bytes.
        connection.sendall(b" 28.0 \n\n1\n")

    server = instrument_server(script)
    with TcpInstrument(server.host, server.port, timeout=0.5) as client:
        got = client.query_many(commands)
    assert got == [" 28.0 ", "", "1"], "pipeline all writes, then match one reply per command"
    assert commands == ["MEAS:VOLT?", "MEAS:CURR?", "*OPC?"], "do not mutate the caller's list"


def test_e4_empty_batch_has_no_network_traffic(instrument_server) -> None:
    closed = Event()
    server = instrument_server(observe_close(closed))
    with TcpInstrument(server.host, server.port) as client:
        assert client.query_many([]) == [], "no commands means no replies to wait for"
    assert closed.wait(1.0), "empty batch must leave the connection quiet"


def test_e4_repeated_commands_and_followup_query(instrument_server) -> None:
    def script(connection: socket.socket) -> None:
        assert read_command(connection) == b"READ?\n"
        assert read_command(connection) == b"READ?\n"
        connection.sendall(b"3.2\n3.3\n")
        assert read_command(connection) == b"*IDN?\n"
        connection.sendall(b"BENCH,DMM\n")

    server = instrument_server(script)
    with TcpInstrument(server.host, server.port) as client:
        assert client.query_many(["READ?", "READ?"]) == ["3.2", "3.3"], "keep duplicate commands and reply order"
        assert client.query("*IDN?") == "BENCH,DMM", "the same connection must work after a batch"


def test_e4_timeout_names_current_pending_command(instrument_server) -> None:
    def script(connection: socket.socket) -> None:
        assert read_command(connection) == b"MEAS:VOLT?\n"
        assert read_command(connection) == b"MEAS:CURR?\n"
        connection.sendall(b"28.0\n")
        connection.recv(1)

    server = instrument_server(script)
    with TcpInstrument(server.host, server.port, timeout=0.1) as client:
        with pytest.raises(TimeoutError) as failure:
            client.query_many(["MEAS:VOLT?", "MEAS:CURR?"])
        assert "MEAS:CURR?" in str(failure.value), "name the pending reply, not the first batch command"
