from __future__ import annotations

from collections.abc import Iterator
from queue import Empty, Queue
import socket
from threading import Barrier, Event, Lock, Thread, current_thread
from time import perf_counter

import pytest

from starter.workers import Listener, Producer, drain, run_pipeline


def test_e1_reads_until_source_exhausted() -> None:
    readings = iter([28.1, None, 28.2])
    output: Queue[object] = Queue()
    stop = Event()
    producer = Producer(lambda: next(readings), output, stop)
    assert isinstance(producer, Thread), "Producer must subclass Thread"
    assert not producer.is_alive(), "construction must not start the producer"
    try:
        producer.start()
        producer.join(timeout=2)
        assert not producer.is_alive(), "StopIteration must finish the producer"
        assert [output.get_nowait() for _ in range(3)] == [28.1, None, 28.2]
        with pytest.raises(Empty):
            output.get_nowait()
    finally:
        stop.set()
        if producer.ident is not None:
            producer.join(timeout=2)
        assert not producer.is_alive(), "producer leaked a thread"


def test_e1_preset_stop_never_calls_source() -> None:
    calls: list[str] = []
    stop = Event()
    stop.set()
    output: Queue[object] = Queue()
    producer = Producer(lambda: calls.append("read"), output, stop)
    try:
        producer.start()
        producer.join(timeout=2)
        assert not producer.is_alive()
        assert calls == [], "an already-stopped producer must not read"
        with pytest.raises(Empty):
            output.get_nowait()
    finally:
        producer.join(timeout=2)


def test_e1_discards_read_that_sets_stop() -> None:
    stop = Event()
    output: Queue[object] = Queue()

    def source() -> object:
        stop.set()
        return "late CH1 reading"

    producer = Producer(source, output, stop)
    try:
        producer.start()
        producer.join(timeout=2)
        assert not producer.is_alive()
        with pytest.raises(Empty):
            output.get_nowait()
    finally:
        stop.set()
        producer.join(timeout=2)


def test_e1_external_stop_during_read() -> None:
    entered = Event()
    release = Event()
    stop = Event()
    output: Queue[object] = Queue()

    def source() -> object:
        entered.set()
        # Only the controller releases this read; the timeout guards deadlock.
        assert release.wait(timeout=5), "controller never released the source"
        return 28.4

    producer = Producer(source, output, stop)
    try:
        producer.start()
        assert entered.wait(timeout=5), "producer never called the source"
        stop.set()
        release.set()
        producer.join(timeout=2)
        assert not producer.is_alive(), "producer ignored stop_event"
        with pytest.raises(Empty):
            output.get_nowait()
    finally:
        stop.set()
        release.set()
        producer.join(timeout=2)


def test_e2_zero_timeout_preserves_queue_order() -> None:
    q: Queue[object] = Queue()
    for item in ["CH1", None, "CH1", 0]:
        q.put_nowait(item)
    assert drain(q, 0) == ["CH1", None, "CH1", 0]
    assert drain(q, 0) == []


def test_e2_negative_timeout_leaves_queue_untouched() -> None:
    q: Queue[str] = Queue()
    q.put_nowait("CH2")
    with pytest.raises(ValueError):
        drain(q, -0.1)
    assert q.get_nowait() == "CH2", "validate before removing readings"


def test_e2_waits_with_get_instead_of_polling() -> None:
    class CheckedQueue(Queue[int]):
        def get(self, block: bool = True, timeout: float | None = None) -> int:
            assert block and timeout == 0.01, "use get(timeout=timeout) on every read"
            return super().get(block=block, timeout=timeout)

        def empty(self) -> bool:
            pytest.fail("empty() is a snapshot, not a waiting strategy")

        def qsize(self) -> int:
            pytest.fail("qsize() is a snapshot, not a waiting strategy")

    q = CheckedQueue()
    q.put_nowait(28)
    assert drain(q, 0.01) == [28]


def test_e2_accepts_arrival_while_get_is_waiting() -> None:
    waiting = Event()
    reading_sent = Event()

    class SignallingQueue(Queue[str]):
        def get(self, block: bool = True, timeout: float | None = None) -> str:
            waiting.set()
            # Script arrival before starting the real queue's idle timeout.
            assert reading_sent.wait(timeout=5), "sender never queued the reading"
            return super().get(block=block, timeout=timeout)

    q = SignallingQueue()

    def send_reading() -> None:
        if waiting.wait(timeout=5):
            q.put_nowait("CH3 ready")
            reading_sent.set()

    sender = Thread(target=send_reading)
    sender.start()
    try:
        assert drain(q, 0.1) == ["CH3 ready"], "wait for a reading arriving after drain begins"
    finally:
        waiting.set()
        sender.join(timeout=5)
        assert not sender.is_alive()


class ObservedSocket(socket.socket):
    """Let tests coordinate on a real socket timeout without sleeping."""

    def __init__(self) -> None:
        super().__init__(socket.AF_INET, socket.SOCK_DGRAM)
        self.timed_out = Event()

    def recvfrom(self, bufsize: int, flags: int = 0) -> tuple[bytes, tuple[str, int]]:
        try:
            return super().recvfrom(bufsize, flags)
        except socket.timeout:
            self.timed_out.set()
            raise


@pytest.fixture
def udp_socket() -> Iterator[ObservedSocket]:
    with ObservedSocket() as sock:
        sock.bind(("127.0.0.1", 0))
        yield sock


def send(sock: socket.socket, packet: bytes) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.bind(("127.0.0.1", 0))
        sender.settimeout(0.2)
        sender.sendto(packet, sock.getsockname())


def test_e3_parses_in_order_and_skips_bad_packets(udp_socket: ObservedSocket) -> None:
    output: Queue[object] = Queue()
    listener = Listener(udp_socket, output, lambda packet: float(packet.decode("ascii")))
    try:
        assert listener.thread is None, "constructor must not start receiving"
        assert not listener.stop_event.is_set()
        assert udp_socket.gettimeout() == 0.2
        listener.start()
        for packet in [b"bad", b"28.1", b"28.2"]:
            send(udp_socket, packet)
        assert output.get(timeout=1) == 28.1
        assert output.get(timeout=1) == 28.2
    finally:
        listener.stop()
        assert listener.thread is None or not listener.thread.is_alive()
    assert udp_socket.fileno() == -1, "stop must close the owned socket"
    with pytest.raises(Empty):
        output.get_nowait()


def test_e3_none_is_a_valid_parsed_item(udp_socket: ObservedSocket) -> None:
    output: Queue[object] = Queue()
    listener = Listener(udp_socket, output, lambda packet: None)
    try:
        listener.start()
        send(udp_socket, b"heartbeat")
        assert output.get(timeout=1) is None
    finally:
        listener.stop()
        assert listener.thread is None or not listener.thread.is_alive()


def test_e3_timeout_keeps_listening_then_idle_stop_is_bounded(udp_socket: ObservedSocket) -> None:
    output: Queue[object] = Queue()
    listener = Listener(udp_socket, output, lambda packet: packet.decode("ascii"))
    try:
        listener.start()
        assert udp_socket.timed_out.wait(timeout=1), "recvfrom must time out while idle"
        assert listener.thread is not None and listener.thread.is_alive(), "timeout must not end the loop"
        send(udp_socket, b"CH4:PASS")
        assert output.get(timeout=1) == "CH4:PASS"
    finally:
        before = perf_counter()
        listener.stop()
        elapsed = perf_counter() - before
        assert listener.thread is None or not listener.thread.is_alive(), "stop returned with a live thread"
    assert elapsed <= 2, f"idle shutdown took {elapsed:.3f}s; limit is 2s"
    assert listener.stop_event.is_set()


def test_e3_repeated_stop_and_start_rejection(udp_socket: ObservedSocket) -> None:
    listener = Listener(udp_socket, Queue(), lambda packet: packet)
    try:
        listener.start()
        with pytest.raises(RuntimeError):
            listener.start()
    finally:
        listener.stop()
        assert listener.thread is None or not listener.thread.is_alive()
    listener.stop()
    with pytest.raises(RuntimeError):
        listener.start()


def test_e3_stop_before_start_closes_socket(udp_socket: ObservedSocket) -> None:
    listener = Listener(udp_socket, Queue(), lambda packet: packet)
    listener.stop()
    listener.stop()
    assert udp_socket.fileno() == -1
    assert listener.thread is None
    assert listener.stop_event.is_set()
    with pytest.raises(RuntimeError):
        listener.start()

@pytest.mark.parametrize("workers", [1, 2, 8])
def test_e4_preserves_duplicate_and_none_inputs(workers: int) -> None:
    values = ["CH1", None, "CH1", "CH2"]
    calls: Queue[object] = Queue()

    def check(item: object) -> str:
        calls.put_nowait(item)
        return f"{item}:PASS"

    assert run_pipeline(iter(values), workers, check) == [f"{item}:PASS" for item in values]
    observed = [calls.get_nowait() for _ in values]
    assert observed.count("CH1") == 2 and observed.count(None) == 1 and observed.count("CH2") == 1
    with pytest.raises(Empty):
        calls.get_nowait()


@pytest.mark.parametrize("workers", [0, -2])
def test_e4_rejects_worker_count_before_consuming_input(workers: int) -> None:
    def readings() -> Iterator[str]:
        pytest.fail("validate workers before consuming the input")
        yield "CH1"

    with pytest.raises(ValueError):
        run_pipeline(readings(), workers, str)
    with pytest.raises(ValueError):
        run_pipeline([], workers, str)


def test_e4_empty_input_starts_no_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_start(self: Thread) -> None:
        pytest.fail("empty input must not start threads")

    def unexpected_check(item: object) -> object:
        pytest.fail("empty input must not call fn")

    monkeypatch.setattr(Thread, "start", unexpected_start)
    assert run_pipeline(iter([]), 3, unexpected_check) == []


def test_e4_uses_requested_pool_and_joins_all_workers() -> None:
    rendezvous = Barrier(3)
    seen: set[Thread] = set()
    guard = Lock()

    def check(channel: int) -> int:
        with guard:
            seen.add(current_thread())
        # A sequential implementation cannot get three checks to this point.
        rendezvous.wait(timeout=0.2)
        return channel * 10

    assert run_pipeline(range(6), 3, check) == [0, 10, 20, 30, 40, 50]
    assert len(seen) == 3, f"expected three worker threads, saw {len(seen)}"
    assert current_thread() not in seen, "fn belongs in the worker pool"
    assert all(not thread.is_alive() for thread in seen), "workers must stop before returning"


def test_e4_returns_input_order_despite_reverse_completion() -> None:
    second_done = Event()
    completions: Queue[int] = Queue()

    def check(channel: int) -> str:
        if channel == 0:
            assert second_done.wait(timeout=0.2), "two workers must overlap"
        completions.put_nowait(channel)
        if channel == 1:
            second_done.set()
        return f"CH{channel}:PASS"

    assert run_pipeline([0, 1], 2, check) == ["CH0:PASS", "CH1:PASS"]
    assert [completions.get_nowait(), completions.get_nowait()] == [1, 0]


@pytest.mark.parametrize("workers", [1, 3])
def test_e4_raises_original_first_error_after_all_checks_stop(workers: int) -> None:
    first = ValueError("CH0 overvoltage")
    later = RuntimeError("CH2 instrument fault")
    attempted: Queue[int] = Queue()
    finished: Queue[int] = Queue()
    seen: set[Thread] = set()
    guard = Lock()
    hold_check = Event()

    def check(channel: int) -> int:
        with guard:
            seen.add(current_thread())
        attempted.put_nowait(channel)
        if channel == 0:
            raise first
        if channel == 2:
            raise later
        # Leave other work in progress when a parallel worker reports failure.
        hold_check.wait(timeout=0.01)
        finished.put_nowait(channel)
        return channel

    with pytest.raises((ValueError, RuntimeError)) as caught:
        run_pipeline(range(5), workers, check)
    if isinstance(caught.value, NotImplementedError):
        raise caught.value
    if workers == 1:
        assert caught.value is first, "re-raise the first recorded exception object"
    else:
        assert caught.value is first or caught.value is later, "do not replace the original exception"
    assert all(not thread.is_alive() for thread in seen), "exception escaped with live workers"
    assert sorted(attempted.get_nowait() for _ in range(5)) == list(range(5)), "attempt every job"
    assert sorted(finished.get_nowait() for _ in range(3)) == [1, 3, 4], "finish remaining checks before raising"
    with pytest.raises(Empty):
        attempted.get_nowait()


from starter.workers import gil_answers


def test_e5_q1_bytecode_execution() -> None:
    answers = gil_answers()
    if not isinstance(answers, dict) or set(answers) != {"Q1", "Q2", "Q3", "Q4"}:
        pytest.fail("E5: return a dictionary with exactly Q1-Q4; reread E5's return contract", pytrace=False)
    if answers.get("Q1") != "B":
        pytest.fail("Q1: reread the Python glossary, 'global interpreter lock', and threading docs, 'GIL and performance considerations'", pytrace=False)


def test_e5_q2_instrument_io_waits() -> None:
    if gil_answers().get("Q2") != "C":
        pytest.fail("Q2: reread threading docs, 'GIL and performance considerations', on I/O-bound tasks", pytrace=False)


def test_e5_q3_cpu_heavy_waveforms() -> None:
    if gil_answers().get("Q3") != "A":
        pytest.fail("Q3: reread the Python glossary, 'global interpreter lock', and threading docs, 'GIL and performance considerations'", pytrace=False)


def test_e5_q4_shared_measurement_counter() -> None:
    if gil_answers().get("Q4") != "D":
        pytest.fail("Q4: reread threading docs, 'Lock objects', and queue docs, 'Queue objects'", pytrace=False)
