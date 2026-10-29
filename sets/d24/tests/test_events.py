from time import perf_counter
import tracemalloc

import pytest

from starter.sequence import EventCounter


class FakeClock:
    """Advance time explicitly instead of sleeping during a test."""

    def __init__(self, now: int = 0) -> None:
        self.now = now

    def __call__(self) -> int:
        return self.now


def test_e5_empty_independent_and_idle_expiry() -> None:
    clock = FakeClock(50_000)
    counter = EventCounter(clock)
    assert len(counter) == 0
    assert counter.count_last(0) == counter.count_last(10_000) == 0
    assert counter.record() is None, "record adds an event and returns None"
    other = EventCounter(clock)
    assert len(other) == other.count_last(10_000) == 0, "instances need independent history"
    clock.now += 10_000
    assert len(counter) == 1, "an event exactly 10,000 ms old must remain stored"
    clock.now += 1
    assert len(counter) == 0, "len must expire events even when no new drops arrive"
    counter.record()
    clock.now += 10_001
    assert counter.count_last(10_000) == 0, "queries must expire idle history too"
    assert len(counter) == 0


@pytest.mark.parametrize("ms,expected", [(0, 1), (1, 2), (9_999, 3), (10_000, 4)])
def test_e5_inclusive_boundaries(ms: int, expected: int) -> None:
    clock = FakeClock(1_000_000)
    counter = EventCounter(clock)
    for timestamp in [1_000_000, 1_000_001, 1_009_999, 1_010_000]:
        clock.now = timestamp
        counter.record()
    got = counter.count_last(ms)
    assert type(got) is int and got == expected, f"window {ms} ms includes both ends: expected {expected}, got {got}"
    assert counter.count_last(0) == 1, "a wider query must not discard events needed by a later query"
    assert counter.count_last(10_000) == 4, "a narrow query must retain the rest of the 10,000 ms history"
    clock.now += 1
    assert counter.count_last(10_000) == 3, "exclude a drop just before the lower boundary"
    assert len(counter) == 3


def test_e5_many_events_in_one_millisecond() -> None:
    clock = FakeClock(55)
    counter = EventCounter(clock)
    for _ in range(40):
        counter.record()
    assert counter.count_last(0) == len(counter) == 40, "same-ms events are separate drops"
    clock.now = 56
    assert counter.count_last(0) == 0
    assert counter.count_last(1) == 40
    counter.record()
    assert counter.count_last(0) == 1
    assert counter.count_last(1) == len(counter) == 41


@pytest.mark.parametrize("invalid", [-1, 10_001, True, False, 0.0, 10_000.0, "5", None, [], {}])
def test_e5_invalid_window(invalid: int) -> None:
    clock = FakeClock()
    counter = EventCounter(clock)
    counter.record()
    with pytest.raises(ValueError):
        counter.count_last(invalid)
    assert counter.count_last(0) == 1, "invalid windows must not record or remove current events"


def test_e5_bounded_history_after_long_run() -> None:
    clock = FakeClock()
    counter = EventCounter(clock)
    tracemalloc.start()
    try:
        for number in range(200_000):
            clock.now = number // 3
            counter.record()
            if number % 10_000 == 0 or number == 199_999:
                expected = number - max(0, 3 * (clock.now - 10_000)) + 1
                assert len(counter) == expected, "retain exactly the events in the last 10,000 ms"
                assert len(counter) <= 30_003, "storage must not grow with the whole station run"
            if number == 49_999:
                warm_bytes = tracemalloc.get_traced_memory()[0]
        growth = tracemalloc.get_traced_memory()[0] - warm_bytes
        # Both samples have 30,002 live events. Allow ample compaction slack;
        # retaining all 150,000 additional timestamps grows by over 5 MB.
        assert growth <= 2_000_000, (
            f"storage grew by {growth:,} bytes with the same live window; "
            "discard expired timestamps from auxiliary storage too"
        )
    finally:
        tracemalloc.stop()
    clock.now += 1_000_000
    counter.record()
    assert len(counter) == counter.count_last(10_000) == 1, "a large time jump must clear all expired history"


def test_e5_fast_enough() -> None:
    clock = FakeClock()
    counter = EventCounter(clock)
    started = perf_counter()
    for number in range(200_000):
        clock.now = number // 4
        counter.record()
    for number in range(200_000):
        ms = (number * 37) % 10_001
        assert counter.count_last(ms) == 4 * (ms + 1), "queries may request windows in any order"
        if number % 1_000 == 0:
            assert perf_counter() - started <= 2.0, "avoid scanning every stored event on each query"
    elapsed = perf_counter() - started
    assert elapsed <= 2.0, f"200,000 records and 200,000 queries took {elapsed:.3f}s; use a fast window lookup"
