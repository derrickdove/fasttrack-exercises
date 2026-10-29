"""Each exercise uses its own sockets, independent of earlier learner functions."""

from collections.abc import Callable, Iterator
from types import SimpleNamespace
import socket
from unittest.mock import Mock

import pytest

from starter import udp
from starter.udp import echo_once, make_receiver, receive_all, send_datagram


@pytest.fixture
def station_socket() -> Iterator[Callable[[], socket.socket]]:
    """Own every local socket and close it even after a failed assertion."""
    opened: list[socket.socket] = []

    def open_socket() -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        opened.append(sock)
        sock.settimeout(0.5)
        sock.bind(("127.0.0.1", 0))
        return sock

    yield open_socket
    for sock in opened:
        sock.close()


@pytest.fixture
def temporary_senders(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[socket.socket]]:
    """Observe real E2 sockets without changing the sockets used by the tests."""
    opened: list[socket.socket] = []

    def tracked_socket(*args, **kwargs) -> socket.socket:
        sock = socket.socket(*args, **kwargs)
        opened.append(sock)
        return sock

    monkeypatch.setattr(
        udp,
        "socket",
        SimpleNamespace(
            socket=tracked_socket,
            AF_INET=socket.AF_INET,
            SOCK_DGRAM=socket.SOCK_DGRAM,
            timeout=socket.timeout,
        ),
    )
    yield opened
    for sock in opened:
        sock.close()


def test_e1_defaults_open_a_bound_udp_socket() -> None:
    with make_receiver() as receiver:
        host, port = receiver.getsockname()
        assert host == "127.0.0.1", "bind the station to loopback"
        assert port > 0, "port 0 must become an operating-system-assigned port"
        assert receiver.family == socket.AF_INET, "use IPv4"
        assert receiver.type == socket.SOCK_DGRAM, "use a UDP datagram socket"
        assert receiver.gettimeout() == 0.5, "default receive timeout is 0.5 seconds"


@pytest.mark.parametrize("timeout", [0.03, 0.15])
def test_e1_uses_requested_timeout(timeout: float) -> None:
    with make_receiver(host="127.0.0.1", port=0, timeout=timeout) as receiver:
        assert receiver.gettimeout() == timeout, "honor the caller's timeout"
        with pytest.raises(socket.timeout):
            receiver.recvfrom(65535)


def test_e1_returned_socket_can_receive(station_socket) -> None:
    sender = station_socket()
    with make_receiver() as receiver:
        sender.sendto(b"instrument=online", receiver.getsockname())
        payload, address = receiver.recvfrom(65535)
        assert payload == b"instrument=online", "return a usable, bound receiver"
        assert address == sender.getsockname(), "recvfrom must identify the sender"


def test_e1_failed_setup_closes_new_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    failed_socket = Mock(spec=socket.socket)
    failed_socket.bind.side_effect = OSError("simulated station bind failure")
    factory = Mock(return_value=failed_socket)
    monkeypatch.setattr(
        udp,
        "socket",
        SimpleNamespace(socket=factory, AF_INET=socket.AF_INET, SOCK_DGRAM=socket.SOCK_DGRAM),
    )
    with pytest.raises(OSError, match="simulated station bind failure"):
        make_receiver()
    failed_socket.close.assert_called_once()


@pytest.mark.parametrize("payload", [b"current=2.4", b"", b"\x00\xff\x80\r\n", b"V" * 8192])
def test_e2_preserves_one_datagram(station_socket, payload: bytes) -> None:
    receiver = station_socket()
    result = send_datagram(payload, receiver.getsockname())
    got, _ = receiver.recvfrom(65535)
    assert got == payload, "send exactly the supplied bytes, including empty data"
    assert result is None, "this one-way send returns None"
    receiver.settimeout(0.02)
    with pytest.raises(socket.timeout):
        receiver.recvfrom(65535)


def test_e2_calls_stay_separate(station_socket) -> None:
    receiver = station_socket()
    for payload in (b"volts=24", b"amps=2"):
        send_datagram(payload, receiver.getsockname())
    got = [receiver.recvfrom(65535)[0] for _ in range(2)]
    assert got == [b"volts=24", b"amps=2"], "each call must send its own datagram"


def test_e2_closes_temporary_socket(station_socket, temporary_senders) -> None:
    receiver = station_socket()
    send_datagram(b"station=ready", receiver.getsockname())
    assert receiver.recvfrom(65535)[0] == b"station=ready"
    assert len(temporary_senders) == 1, "one temporary sender is enough"
    assert temporary_senders[0].fileno() == -1, "close the temporary sender after sending"
    assert temporary_senders[0].gettimeout() == 0.5, "bound the send wait to 0.5 seconds"


def test_e2_send_error_propagates_and_closes(station_socket, temporary_senders) -> None:
    receiver = station_socket()
    # 70,000 bytes cannot fit in one IPv4 UDP datagram on Windows or Linux.
    with pytest.raises(OSError):
        send_datagram(b"X" * 70000, receiver.getsockname())
    assert len(temporary_senders) == 1, "attempt one datagram using one sender"
    assert temporary_senders[0].fileno() == -1, "close the sender even when sendto fails"


def test_e3_collects_complete_payloads(station_socket) -> None:
    receiver, sender = station_socket(), station_socket()
    payloads = [b"V=24", b"", b"\x00\xff", b"waveform=" + b"x" * 8192]
    for payload in payloads:
        sender.sendto(payload, receiver.getsockname())
    got = receive_all(receiver, len(payloads), 0.05)
    assert got == payloads, "keep message boundaries, empty packets, and all payload bytes"
    assert receiver.gettimeout() == 0.5, "restore the timeout after reaching the count"
    assert receiver.fileno() != -1, "the caller still owns the receiver"


def test_e3_maximum_leaves_excess_queued(station_socket) -> None:
    receiver, sender = station_socket(), station_socket()
    for payload in (b"step=1", b"step=2", b"step=3"):
        sender.sendto(payload, receiver.getsockname())
    assert receive_all(receiver, 2, 0.05) == [b"step=1", b"step=2"]
    assert receiver.recvfrom(65535)[0] == b"step=3", "stop reading at max_packets"


def test_e3_idle_returns_empty_and_restores_timeout(station_socket) -> None:
    receiver = station_socket()
    receiver.settimeout(0.12)
    assert receive_all(receiver, 3, 0.02) == [], "idle is a normal empty batch"
    assert receiver.gettimeout() == 0.12, "restore the caller's timeout after idle"
    assert receiver.fileno() != -1, "idle does not close the receiver"


def test_e3_zero_maximum_reads_nothing(station_socket) -> None:
    receiver, sender = station_socket(), station_socket()
    sender.sendto(b"pending", receiver.getsockname())
    assert receive_all(receiver, 0, 0.02) == [], "zero maximum means no reads"
    assert receiver.gettimeout() == 0.5, "zero maximum leaves the timeout alone"
    assert receiver.recvfrom(65535)[0] == b"pending", "leave the queued message untouched"


def test_e3_each_receive_gets_full_idle_timeout() -> None:
    # A scripted socket avoids scheduler delays when checking each receive's timeout.
    receiver = Mock(spec=socket.socket)
    current_timeout = 0.5
    waits: list[float] = []
    events = iter([(b"V=24", ("127.0.0.1", 42000)), (b"I=2", ("127.0.0.1", 42000))])

    def set_timeout(value: float) -> None:
        nonlocal current_timeout
        current_timeout = value

    def receive(size: int) -> tuple[bytes, tuple[str, int]]:
        waits.append(current_timeout)
        assert size >= 65535, "receive a complete datagram without truncation"
        try:
            return next(events)
        except StopIteration:
            raise socket.timeout("simulated idle") from None

    receiver.gettimeout.side_effect = lambda: current_timeout
    receiver.settimeout.side_effect = set_timeout
    receiver.recvfrom.side_effect = receive
    got = receive_all(receiver, 5, 0.05)
    assert got == [b"V=24", b"I=2"], "return the partial batch on idle"
    assert waits == [0.05, 0.05, 0.05], "give every receive a fresh full idle timeout"
    assert current_timeout == 0.5, "restore the original timeout"
    receiver.close.assert_not_called()


def test_e3_other_receive_errors_propagate_with_timeout_restored() -> None:
    receiver = Mock(spec=socket.socket)
    receiver.gettimeout.return_value = 0.5
    receiver.recvfrom.side_effect = OSError("simulated receiver fault")
    with pytest.raises(OSError, match="simulated receiver fault"):
        receive_all(receiver, 3, 0.05)
    assert receiver.settimeout.call_args.args == (0.5,), "restore timeout even after an error"
    receiver.close.assert_not_called()


@pytest.mark.parametrize("payload", [b"ready?", b"", b"ch2=ok\x00\xff", b"a" * 8192])
def test_e4_echoes_uppercase_from_receiver_address(station_socket, payload: bytes) -> None:
    receiver, instrument = station_socket(), station_socket()
    instrument.sendto(payload, receiver.getsockname())
    sender = echo_once(receiver)
    reply, reply_source = instrument.recvfrom(65535)
    assert reply == payload.upper(), "uppercase only ASCII letters and preserve all other bytes"
    assert sender == instrument.getsockname(), "return the original sender's address"
    assert reply_source == receiver.getsockname(), "reply using the supplied receiver socket"
    assert receiver.gettimeout() == 0.5, "keep the caller's timeout unchanged"
    assert receiver.fileno() != -1, "keep the caller's receiver open"
    instrument.settimeout(0.02)
    with pytest.raises(socket.timeout):
        instrument.recvfrom(65535)


def test_e4_handles_exactly_one_message(station_socket) -> None:
    receiver, instrument = station_socket(), station_socket()
    instrument.sendto(b"first", receiver.getsockname())
    instrument.sendto(b"second", receiver.getsockname())
    echo_once(receiver)
    assert instrument.recvfrom(65535)[0] == b"FIRST"
    assert receiver.recvfrom(65535)[0] == b"second", "one call consumes only one datagram"


def test_e4_replies_to_each_actual_sender(station_socket) -> None:
    receiver = station_socket()
    instruments = [station_socket(), station_socket()]
    for number, instrument in enumerate(instruments):
        payload = f"instrument={number}".encode("ascii")
        instrument.sendto(payload, receiver.getsockname())
        assert echo_once(receiver) == instrument.getsockname(), "use this datagram's sender"
        assert instrument.recvfrom(65535)[0] == payload.upper(), "route the reply to that sender"


def test_e4_receive_timeout_propagates(station_socket) -> None:
    receiver = station_socket()
    receiver.settimeout(0.02)
    with pytest.raises(socket.timeout):
        echo_once(receiver)
    assert receiver.gettimeout() == 0.02, "don't change the caller's timeout on error"
    assert receiver.fileno() != -1, "a timeout does not transfer socket ownership"


def test_e4_send_error_propagates() -> None:
    receiver = Mock(spec=socket.socket)
    receiver.recvfrom.return_value = (b"ready?", ("127.0.0.1", 42000))
    receiver.sendto.side_effect = OSError("simulated reply failure")
    with pytest.raises(OSError, match="simulated reply failure"):
        echo_once(receiver)
    receiver.settimeout.assert_not_called()
    receiver.close.assert_not_called()


def test_e5_q1_high_rate_telemetry() -> None:
    answers = udp.transport_answers()
    if (
        not isinstance(answers, dict)
        or set(answers) != {"Q1", "Q2", "Q3", "Q4"}
        or answers.get("Q1") != "B"
    ):
        pytest.fail(
            "Q1: Return the four question ids and reread Beej, Two Types of "
            "Internet Sockets, on time-sensitive datagrams.",
            pytrace=False,
        )


def test_e5_q2_power_supply_commands() -> None:
    answers = udp.transport_answers()
    if not isinstance(answers, dict) or answers.get("Q2") != "C":
        pytest.fail(
            "Q2: Reread Beej, Two Types of Internet Sockets, on reliable delivery.",
            pytrace=False,
        )


def test_e5_q3_udp_ordering_and_delivery() -> None:
    answers = udp.transport_answers()
    if not isinstance(answers, dict) or answers.get("Q3") != "A":
        pytest.fail(
            "Q3: Reread Beej, Two Types of Internet Sockets, on datagram "
            "guarantees and packet numbering.",
            pytrace=False,
        )


def test_e5_q4_message_boundaries() -> None:
    answers = udp.transport_answers()
    if not isinstance(answers, dict) or answers.get("Q4") != "D":
        pytest.fail(
            "Q4: Reread Beej, Two Types of Internet Sockets, and Son of Data "
            "Encapsulation, on stream data and message lengths.",
            pytrace=False,
        )
