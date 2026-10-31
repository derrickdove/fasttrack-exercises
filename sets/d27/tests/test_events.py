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


def test_e5_bounded_history_across_expiry_windows() -> None:
    clock = FakeClock(20_000)
    counter = EventCounter(clock)
    for number in range(40):
        clock.now = 20_000 + number * 1_000
        counter.record()
        expected = min(number + 1, 11)
        assert len(counter) == expected, "retain only the inclusive 10,000 ms history"
        assert counter.count_last(10_000) == expected
        assert counter.count_last(0) == 1, "each new timestamp has one drop"
    clock.now += 10_001
    counter.record()
    assert len(counter) == counter.count_last(10_000) == 1, "a large time jump must clear expired history"

    clock = FakeClock()
    counter = EventCounter(clock)
    tracemalloc.start()
    try:
        warm_bytes = 0
        for number in range(200_000):
            clock.now = number // 3
            counter.record()
            if number == 49_999 or number == 199_999:
                assert len(counter) == 30_002, "both memory samples must have the same live window"
                if number == 49_999:
                    warm_bytes = tracemalloc.get_traced_memory()[0]
        growth = tracemalloc.get_traced_memory()[0] - warm_bytes
        # Allow ample storage slack for the same 30,002 live events.
        # Keeping all 150,000 additional timestamps grows by over 5 MB.
        assert growth <= 2_000_000, (
            f"storage grew by {growth:,} bytes with the same live window; "
            "discard expired timestamps from extra storage too"
        )
    finally:
        tracemalloc.stop()


def test_e5_arbitrary_windows_follow_injected_clock() -> None:
    clock = FakeClock(70_000)
    counter = EventCounter(clock)
    for timestamp in [70_000, 70_003, 70_003, 70_008, 70_010]:
        clock.now = timestamp
        counter.record()
    for ms, expected in [(0, 1), (10_000, 5), (2, 2), (7, 4), (1, 1), (10, 5), (0, 1)]:
        assert counter.count_last(ms) == expected, f"window {ms} ms should contain {expected} drops"
    clock.now = 70_013
    assert counter.count_last(2) == 0, "queries must read the injected clock after it advances"
    assert counter.count_last(3) == 1
    assert counter.count_last(10) == 4, "include both drops at the lower boundary"
    assert len(counter) == 5, "short queries must preserve events for wider queries"
