"""Serial loopback and local TCP contracts, without instrument hardware."""

from contextlib import contextmanager, nullcontext
import queue
import socket
import threading
import time

import pytest
import serial


@pytest.fixture
def loop_ports(monkeypatch):
    """Observe real loop ports without depending on learner attribute names."""
    open_port = serial.serial_for_url
    ports = []
    options = []

    def recording_open(url, **kwargs):
        port = open_port(url, **kwargs)
        ports.append(port)
        options.append((url, kwargs))
        return port

    monkeypatch.setattr(serial, "serial_for_url", recording_open)
    try:
        yield ports, options
    finally:
        for port in ports:
            port.close()


@pytest.fixture
def serial_instruments(loop_ports, import_isolated_instruments):
    # Install the port observer before either style of serial import.
    return import_isolated_instruments()


def play_serial_instrument(port, monkeypatch, replies, terminator=b"\n"):
    """Consume each command's loopback echo before putting a reply on that port."""
    send = port.write
    commands = []

    def instrument_write(data):
        count = send(data)
        wire = port.read_until(terminator)
        assert wire == data, "the whole command must reach the serial port"
        assert wire.endswith(terminator), "each command needs its terminator"
        command = wire[:-len(terminator)].decode("ascii")
        commands.append(command)
        reply = replies.get(command)
        if reply is not None:
            send(reply)
        return count

    monkeypatch.setattr(port, "write", instrument_write)
    return commands


class ScpiServer:
    """One bounded, joined worker serving one client on an OS-assigned port."""

    def __init__(self, replies, terminator=b"\n"):
        self.replies = replies
        self.terminator = terminator
        self.commands = queue.Queue()
        self.disconnected = threading.Event()
        self.stop = threading.Event()
        self.errors = []
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.settimeout(0.1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self.serve, name="gate-b3-scpi")
        self.thread.start()

    def serve(self):
        try:
            while not self.stop.is_set():
                try:
                    connection, _ = self.listener.accept()
                    break
                except socket.timeout:
                    continue
            else:
                return
            with connection:
                connection.settimeout(0.1)
                pending = b""
                while not self.stop.is_set():
                    try:
                        data = connection.recv(4096)
                    except socket.timeout:
                        continue
                    if not data:
                        self.disconnected.set()
                        return
                    pending += data
                    while self.terminator in pending:
                        command, pending = pending.split(self.terminator, 1)
                        self.commands.put(command + self.terminator)
                        for part in self.replies.get(command.decode("ascii"), ()):
                            connection.sendall(part)
        except Exception as error:
            self.errors.append(error)

    def close(self):
        self.stop.set()
        try:
            self.thread.join(timeout=2.0)
            assert not self.thread.is_alive(), "fake SCPI server did not stop"
            assert not self.errors, f"fake SCPI server failed: {self.errors}"
        finally:
            self.listener.close()


@pytest.fixture
def tcp_server():
    @contextmanager
    def start(replies=None, terminator=b"\n"):
        server = ScpiServer(replies or {}, terminator)
        try:
            yield server
        finally:
            server.close()
    return start


@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
def test_serial_write_frames_ascii_and_opens_url(serial_instruments, loop_ports, terminator):
    instruments = serial_instruments
    ports, options = loop_ports
    kwargs = {} if terminator == "\n" else dict(baudrate=19200, terminator=terminator)
    with instruments.SerialTransport("loop://", **kwargs) as transport:
        port = ports[-1]
        assert options == [("loop://", dict(baudrate=19200 if kwargs else 9600, timeout=1.0))]
        assert transport.write("VOLT 5.000") is None
        assert port.read_until(terminator.encode("ascii")) == ("VOLT 5.000" + terminator).encode("ascii")


@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
def test_serial_query_reads_and_strips_loop_echo(serial_instruments, terminator):
    instruments = serial_instruments
    with instruments.SerialTransport("loop://", timeout=0.5, terminator=terminator) as transport:
        assert transport.query("  *IDN?  ") == "*IDN?"


@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
def test_serial_query_reads_instrument_reply(serial_instruments, loop_ports, monkeypatch, terminator):
    instruments = serial_instruments
    with instruments.SerialTransport("loop://", timeout=0.5, terminator=terminator) as transport:
        commands = play_serial_instrument(
            loop_ports[0][-1], monkeypatch,
            {"*IDN?": b" \tFASTTRACK,SERIAL,SIM,1.0 " + terminator.encode("ascii")},
            terminator.encode("ascii"),
        )
        assert transport.query("*IDN?") == "FASTTRACK,SERIAL,SIM,1.0"
        assert commands == ["*IDN?"]


@pytest.mark.parametrize("reply", [b"", b"24.125"], ids=["silent", "unterminated"])
def test_serial_timeout_names_command(serial_instruments, loop_ports, monkeypatch, reply):
    instruments = serial_instruments
    with instruments.SerialTransport("loop://", timeout=0.1) as transport:
        play_serial_instrument(loop_ports[0][-1], monkeypatch, {"MEAS:VOLT?": reply})
        started = time.monotonic()
        with pytest.raises(TimeoutError) as caught:
            transport.query("MEAS:VOLT?")
        assert "MEAS:VOLT?" in str(caught.value)
        assert time.monotonic() - started < 1.0, "query must not wait forever for a terminator"


def test_serial_close_releases_port(serial_instruments, loop_ports):
    instruments = serial_instruments
    transport = instruments.SerialTransport("loop://", timeout=0.1)
    try:
        assert loop_ports[0][-1].is_open
        assert transport.close() is None
        assert not loop_ports[0][-1].is_open
    finally:
        transport.close()


@pytest.mark.parametrize("fail_body", [False, True])
def test_serial_context_closes_and_preserves_body_exception(serial_instruments, loop_ports, fail_body):
    instruments = serial_instruments
    original = RuntimeError("test step failed")
    with pytest.raises(RuntimeError) if fail_body else nullcontext() as caught:
        with instruments.SerialTransport("loop://", timeout=0.1) as transport:
            assert transport is not None and loop_ports[0][-1].is_open
            if fail_body:
                raise original
    if fail_body:
        assert caught.value is original
    assert not loop_ports[0][-1].is_open


@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
def test_tcp_write_frames_ascii(instruments, tcp_server, terminator):
    wire_end = terminator.encode("ascii")
    with tcp_server(terminator=wire_end) as server:
        with instruments.TcpTransport("127.0.0.1", server.port, timeout=0.5, terminator=terminator) as transport:
            assert transport.write("VOLT 5.000") is None
            assert server.commands.get(timeout=1.0) == b"VOLT 5.000" + wire_end


@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
def test_tcp_query_assembles_split_reply(import_isolated_instruments, tcp_server, monkeypatch, terminator):
    create_connection = socket.create_connection

    class SmallReads:
        """Keep actual TCP I/O, while forcing several recv calls on every OS."""
        def __init__(self, connection):
            self.connection = connection

        def recv(self, size):
            return self.connection.recv(min(size, 2))

        def __getattr__(self, name):
            return getattr(self.connection, name)

    def connect(*args, **kwargs):
        return SmallReads(create_connection(*args, **kwargs))

    monkeypatch.setattr(socket, "create_connection", connect)
    instruments = import_isolated_instruments()
    wire_end = terminator.encode("ascii")
    with tcp_server({"*IDN?": [b" \tFAST", b"TRACK,TCP,SIM,1.0 ", wire_end]}, wire_end) as server:
        with instruments.TcpTransport("127.0.0.1", server.port, timeout=0.5, terminator=terminator) as transport:
            assert transport.query("*IDN?") == "FASTTRACK,TCP,SIM,1.0"
            assert server.commands.get(timeout=1.0) == b"*IDN?" + wire_end


def test_tcp_query_keeps_extra_reply_for_next_query(import_isolated_instruments, tcp_server, monkeypatch):
    create_connection = socket.create_connection

    class CombinedRead:
        def __init__(self, connection):
            self.connection = connection
            self.first_read = True

        def recv(self, size):
            if not self.first_read:
                return self.connection.recv(size)
            self.first_read = False
            data = b""
            # Force both replies into one recv result, even if TCP splits them.
            while data.count(b"\n") < 2:
                part = self.connection.recv(size - len(data))
                if not part:
                    break
                data += part
            return data

        def __getattr__(self, name):
            return getattr(self.connection, name)

    def connect(*args, **kwargs):
        return CombinedRead(create_connection(*args, **kwargs))

    monkeypatch.setattr(socket, "create_connection", connect)
    instruments = import_isolated_instruments()
    with tcp_server({"FIRST?": [b" first \n second \n"]}) as server:
        with instruments.TcpTransport("127.0.0.1", server.port, timeout=0.5) as transport:
            assert transport.query("FIRST?") == "first"
            assert transport.query("SECOND?") == "second"
            assert [server.commands.get(timeout=1.0) for _ in range(2)] == [b"FIRST?\n", b"SECOND?\n"]


@pytest.mark.parametrize("reply", [[], [b"24.125"]], ids=["silent", "unterminated"])
def test_tcp_timeout_names_command(instruments, tcp_server, reply):
    with tcp_server({"MEAS:VOLT?": reply}) as server:
        with instruments.TcpTransport("127.0.0.1", server.port, timeout=0.1) as transport:
            started = time.monotonic()
            with pytest.raises(TimeoutError) as caught:
                transport.query("MEAS:VOLT?")
            assert "MEAS:VOLT?" in str(caught.value)
            assert time.monotonic() - started < 1.0, "query must have a bounded receive wait"


def test_tcp_close_disconnects_peer(instruments, tcp_server):
    with tcp_server() as server:
        transport = instruments.TcpTransport("127.0.0.1", server.port, timeout=0.5)
        try:
            assert transport.close() is None
            assert server.disconnected.wait(timeout=1.0), "close must release the TCP connection"
        finally:
            transport.close()


@pytest.mark.parametrize("fail_body", [False, True])
def test_tcp_context_closes_and_preserves_body_exception(instruments, tcp_server, fail_body):
    original = RuntimeError("test step failed")
    with tcp_server() as server:
        with pytest.raises(RuntimeError) if fail_body else nullcontext() as caught:
            with instruments.TcpTransport("127.0.0.1", server.port, timeout=0.5) as transport:
                assert transport is not None
                if fail_body:
                    raise original
        if fail_body:
            assert caught.value is original
        assert server.disconnected.wait(timeout=1.0), "context exit must close the TCP connection"


DRIVER_REPLIES = {
    "*IDN?": b"FASTTRACK,INSTRUMENT,SIM,1.0\n",
    "MEAS:VOLT?": b"24.125\n",
    "MEAS:VOLT:DC?": b"24.125\n",
    "MEAS:CURR:DC?": b"0.125\n",
    "SYST:ERR?": b'0,"No error"\n',
}


def exercise_driver(instruments, transport, driver):
    device = getattr(instruments, driver)(transport)
    assert device.idn() == "FASTTRACK,INSTRUMENT,SIM,1.0"
    if driver == "PowerSupply":
        with device as psu:
            psu.set_voltage(2, 24.0)
            psu.set_current_limit(2, 0.5)
            psu.output(2, True)
            assert psu.measure_voltage(2) == pytest.approx(24.125)
            assert psu.check_errors() is None
        expected = [
            "*IDN?", "INST:NSEL 2", "VOLT 24.000", "INST:NSEL 2", "CURR 0.500",
            "INST:NSEL 2", "OUTP ON", "INST:NSEL 2", "MEAS:VOLT?", "SYST:ERR?",
            "INST:NSEL 1", "OUTP OFF", "INST:NSEL 2", "OUTP OFF", "INST:NSEL 3", "OUTP OFF",
        ]
    else:
        assert device.measure_dc_voltage() == pytest.approx(24.125)
        assert device.measure_dc_current() == pytest.approx(0.125)
        assert device.check_errors() is None
        expected = ["*IDN?", "MEAS:VOLT:DC?", "MEAS:CURR:DC?", "SYST:ERR?"]
    # The driver context must leave its caller's connection usable.
    assert transport.query("SYST:ERR?") == '0,"No error"'
    return expected + ["SYST:ERR?"]


@pytest.mark.parametrize("driver", ["PowerSupply", "Dmm"])
def test_drivers_work_unchanged_over_serial(serial_instruments, loop_ports, monkeypatch, driver):
    instruments = serial_instruments
    with instruments.SerialTransport("loop://", timeout=0.5) as transport:
        commands = play_serial_instrument(loop_ports[0][-1], monkeypatch, DRIVER_REPLIES)
        expected = exercise_driver(instruments, transport, driver)
        assert commands == expected


@pytest.mark.parametrize("driver", ["PowerSupply", "Dmm"])
def test_drivers_work_unchanged_over_tcp(instruments, tcp_server, driver):
    with tcp_server({command: [reply] for command, reply in DRIVER_REPLIES.items()}) as server:
        with instruments.TcpTransport("127.0.0.1", server.port, timeout=0.5) as transport:
            expected = exercise_driver(instruments, transport, driver)
            assert [server.commands.get(timeout=1.0) for _ in expected] == [
                (command + "\n").encode("ascii") for command in expected
            ]
