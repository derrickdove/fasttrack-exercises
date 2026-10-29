"""Local UDP only; queues synchronize callbacks without wall-clock sleeps."""

from queue import Queue
import socket
import threading
from time import perf_counter

import pytest


def test_listener_binds_assigned_port_and_calls_back_on_worker_after_tracking(
    telemetry, listener_factory, send_datagram, wire_packet,
):
    callbacks = Queue()
    main_thread = threading.get_ident()
    with listener_factory(lambda packet: callbacks.put(
        (threading.get_ident(), packet, listener.tracker.received)
    )) as listener:
        listener.start()
        assert 1 <= listener.port <= 65535
        assert isinstance(listener.tracker, telemetry.SequenceTracker)
        send_datagram(listener.port, wire_packet(10, 123, ((2, 5.0),)))
        callback_thread, packet, received = callbacks.get(timeout=1.5)
        assert callback_thread != main_thread
        assert received == 1, "track the packet before calling on_packet"
        assert packet == telemetry.Packet(10, 123, {2: 5.0})
        assert listener.tracker.received == 1
        assert listener.tracker.missing == set()


def test_listener_reports_bad_bytes_and_keeps_receiving(
    telemetry, listener_factory, send_datagram, wire_packet,
):
    packets, errors = Queue(), Queue()
    with listener_factory(packets.put, on_error=lambda data, error: errors.put((data, error))) as listener:
        listener.start()
        corrupt = bytearray(wire_packet())
        corrupt[-1] ^= 1
        bad_packets = [b"bad", bytes(corrupt), wire_packet(readings=((2, 1.0), (2, 2.0)))]
        for bad in bad_packets:
            send_datagram(listener.port, bad)
            data, error = errors.get(timeout=1.5)
            assert data == bad
            assert isinstance(error, telemetry.PacketError)
        send_datagram(listener.port, wire_packet(40))
        assert packets.get(timeout=1.5).seq == 40
        assert listener.tracker.received == 1, "bad datagrams must not reach the tracker"
        assert listener.tracker.missing == set()
        assert errors.empty()


def test_listener_ignores_bad_packet_without_error_callback_and_continues(
    listener_factory, send_datagram, wire_packet,
):
    packets = Queue()
    with listener_factory(packets.put) as listener:
        listener.start()
        send_datagram(listener.port, b"")
        send_datagram(listener.port, wire_packet(50))
        assert packets.get(timeout=1.5).seq == 50
        assert listener.tracker.received == 1


def test_listener_tracks_gaps_late_packets_and_duplicates_and_delivers_each(
    listener_factory, send_datagram, wire_packet,
):
    packets = Queue()
    with listener_factory(packets.put) as listener:
        listener.start()
        for seq in (65534, 1, 65535, 65535):
            send_datagram(listener.port, wire_packet(seq))
            assert packets.get(timeout=1.5).seq == seq
        assert listener.tracker.missing == {0}
        assert listener.tracker.out_of_order == 1
        assert listener.tracker.duplicates == 1


def test_listener_idle_stop_joins_within_two_seconds_and_releases_socket(listener_factory, monkeypatch):
    timeouts = []
    original_settimeout = socket.socket.settimeout

    def record_timeout(sock, timeout):
        timeouts.append(timeout)
        return original_settimeout(sock, timeout)

    monkeypatch.setattr(socket.socket, "settimeout", record_timeout)
    before = set(threading.enumerate())
    with listener_factory(lambda packet: None) as listener:
        listener.start()
        port = listener.port
        workers = set(threading.enumerate()) - before
        assert workers, "start must launch a receiver thread"
        assert 0.2 in timeouts, "receiver needs a 0.2 second socket timeout"
        started = perf_counter()
    assert perf_counter() - started <= 2.0, "stop must finish within two seconds"
    assert not any(thread.is_alive() for thread in workers), "stop must join the receiver"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.settimeout(1.0)
        probe.bind(("127.0.0.1", port))


@pytest.mark.parametrize("body_raises", [False, True], ids=["normal-exit", "exception-exit"])
def test_listener_context_starts_receiving_and_cleans_up(
    telemetry, send_datagram, wire_packet, body_raises,
):
    packets = Queue()
    listener = telemetry.TelemetryListener("127.0.0.1", 0, packets.put)
    before = set(threading.enumerate())
    original = RuntimeError("test step failed")
    try:
        with listener:
            port = listener.port
            workers = set(threading.enumerate()) - before
            send_datagram(port, wire_packet(80))
            assert packets.get(timeout=1.5).seq == 80
            if body_raises:
                raise original
    except RuntimeError as error:
        assert body_raises and error is original
    else:
        assert not body_raises, "context must preserve the body's exception"
    assert not any(thread.is_alive() for thread in workers)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.settimeout(1.0)
        probe.bind(("127.0.0.1", port))
