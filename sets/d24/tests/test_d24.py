from time import perf_counter

import pytest

from starter.sequence import GapTracker, loss_report, missing_between, seq_diff


@pytest.mark.parametrize(
    "a,b,expected",
    [(0, 0, 0), (42, 42, 0), (12, 9, 3), (9, 12, -3),
     (0, 65535, 1), (65535, 0, -1), (1, 65535, 2), (65535, 1, -2)],
)
def test_e1_station_counter_differences(a: int, b: int, expected: int) -> None:
    got = seq_diff(a, b)
    assert got == expected, f"seq_diff({a}, {b}) should be {expected}, got {got}"


@pytest.mark.parametrize(
    "a,b,expected",
    [(32767, 0, 32767), (0, 32767, -32767),
     (32768, 0, -32768), (0, 32768, -32768),
     (65535, 32767, -32768), (0, 32769, 32767)],
)
def test_e1_half_ring_boundary(a: int, b: int, expected: int) -> None:
    assert seq_diff(a, b) == expected, "use the documented negative half-ring tie"


@pytest.mark.parametrize("a,b", [(-1, 0), (65536, 0), (0, -1), (0, 65536)])
def test_e1_rejects_invalid_counter(a: int, b: int) -> None:
    with pytest.raises(ValueError):
        seq_diff(a, b)


@pytest.mark.parametrize(
    "last,new,expected",
    [(10, 14, [11, 12, 13]), (10, 11, []), (65534, 2, [65535, 0, 1]),
     (65535, 0, []), (65535, 2, [0, 1])],
)
def test_e2_station_gap_order(last: int, new: int, expected: list[int]) -> None:
    assert missing_between(last, new) == expected, "list skipped packets in forward order"


@pytest.mark.parametrize("last,new", [(10, 10), (11, 10), (0, 65535), (0, 32768), (32768, 0)])
def test_e2_nonforward_has_no_gap(last: int, new: int) -> None:
    first = missing_between(last, new)
    second = missing_between(last, new)
    assert first == [], "equal, backward and half-ring steps have no gap"
    assert first is not second, "each call must return a fresh list"


def test_e2_largest_forward_gap() -> None:
    gap = missing_between(65530, 32761)
    expected = list(range(65531, 65536)) + list(range(32761))
    assert gap == expected, "a forward distance of 32767 skips 32766 sequence numbers"


@pytest.mark.parametrize("last,new", [(-1, 4), (65536, 0), (3, -1), (0, 65536)])
def test_e2_rejects_invalid_counter(last: int, new: int) -> None:
    with pytest.raises(ValueError):
        missing_between(last, new)


def test_e3_new_station_and_independent_runs() -> None:
    tracker = GapTracker()
    assert (tracker.received, tracker.duplicates, tracker.out_of_order, tracker.missing) == (0, 0, 0, set())
    assert tracker.update(65535) == [], "the first packet cannot establish a gap"
    assert tracker.received == 1
    other = GapTracker()
    assert other.update(100) == []
    assert other.update(103) == [101, 102]
    assert tracker.missing == set(), "separate station runs must not share their missing set"
    assert tracker.update(0) == [], "65535 to 0 is consecutive"
    assert tracker.received == 2


def test_e3_forward_gaps_across_wrap() -> None:
    tracker = GapTracker()
    assert tracker.update(65533) == []
    assert tracker.update(1) == [65534, 65535, 0]
    assert tracker.update(4) == [2, 3]
    assert tracker.missing == {65534, 65535, 0, 2, 3}
    assert (tracker.received, tracker.duplicates, tracker.out_of_order) == (3, 0, 0)


def test_e3_late_repairs_do_not_move_forward_position() -> None:
    tracker = GapTracker()
    tracker.update(65534)
    assert tracker.update(2) == [65535, 0, 1]
    assert tracker.update(0) == []
    assert tracker.missing == {65535, 1}, "late packet 0 repairs its own missing entry"
    assert tracker.update(65533) == [], "an older packet need not have been missing"
    assert tracker.update(32770) == [], "the exact half-ring tie is out of order"
    assert tracker.update(3) == [], "late arrivals must not move the latest forward position"
    assert (tracker.received, tracker.duplicates, tracker.out_of_order) == (6, 0, 3)
    assert tracker.missing == {65535, 1}


def test_e3_duplicates_take_priority_over_ordering() -> None:
    tracker = GapTracker()
    outputs = [tracker.update(seq) for seq in [10, 13, 11, 13, 11, 10, 14]]
    assert outputs == [[], [11, 12], [], [], [], [], []]
    assert (tracker.received, tracker.duplicates, tracker.out_of_order) == (7, 3, 1)
    assert tracker.missing == {12}, "duplicates cannot add gaps or remove other missing entries"


def test_e3_window_is_previous_1024_arrivals_including_repeats() -> None:
    tracker = GapTracker()
    for seq in range(1024):
        tracker.update(seq)
    assert tracker.update(0) == []
    assert tracker.duplicates == 1, "the oldest of 1024 arrivals is still in the duplicate window"
    assert tracker.update(1) == []
    assert tracker.duplicates == 2, "checking a duplicate must not forget another recent number"

    expired = GapTracker()
    for seq in range(1025):
        expired.update(seq)
    assert expired.update(0) == []
    assert (expired.duplicates, expired.out_of_order) == (0, 1), "arrival 0 expired after 1024 newer arrivals"

    repeated = GapTracker()
    repeated.update(0)
    repeated.update(1)
    for _ in range(1023):
        repeated.update(1)
    assert repeated.duplicates == 1023, "evicting one copy must retain membership for other copies"
    assert repeated.update(0) == []
    assert repeated.out_of_order == 1, "repeated arrivals must also age old numbers out of history"
    assert repeated.received == 1026
    assert repeated.update(1) == []
    assert repeated.duplicates == 1024, "recent duplicate copies remain in the window"

    same_position = GapTracker()
    same_position.update(100)
    for _ in range(1024):
        same_position.update(0)
    assert same_position.update(100) == []
    assert same_position.out_of_order == 2, "an expired equal-position packet is nonforward, not a recent duplicate"
    assert same_position.duplicates == 1023


@pytest.mark.parametrize("invalid", [-1, 65536])
def test_e3_rejects_without_changing_state(invalid: int) -> None:
    tracker = GapTracker()
    for seq in range(1024):
        tracker.update(seq)
    with pytest.raises(ValueError):
        tracker.update(invalid)
    assert (tracker.received, tracker.duplicates, tracker.out_of_order, tracker.missing) == (1024, 0, 0, set())
    assert tracker.update(0) == []
    assert tracker.duplicates == 1, "invalid arrivals must not evict valid duplicate history"
    assert tracker.update(1025) == [1024], "invalid arrivals must not change the latest forward position"


@pytest.mark.parametrize("seqs", [[], [60000], [7, 8, 9], [65534, 65535, 0, 1]])
def test_e4_empty_or_complete_capture(seqs: list[int]) -> None:
    got = loss_report(seqs)
    assert got == {"received": len(seqs), "missing": 0, "loss_pct": 0.0, "longest_gap": 0}
    assert isinstance(got["loss_pct"], float), "loss percentage must be a float even with no loss"
    for key in ["received", "missing", "longest_gap"]:
        assert type(got[key]) is int, f"{key} must be an integer count"


@pytest.mark.parametrize(
    "seqs,missing,longest,percent",
    [([10, 13, 18], 6, 4, 100.0 * 6 / 9),
     ([65533, 1, 4], 5, 3, 62.5)],
)
def test_e4_gap_summary(seqs: list[int], missing: int, longest: int, percent: float) -> None:
    got = loss_report(seqs)
    assert set(got) == {"received", "missing", "loss_pct", "longest_gap"}
    assert got["received"] == len(seqs)
    assert got["missing"] == missing
    assert got["longest_gap"] == longest
    assert got["loss_pct"] == pytest.approx(percent), "loss counts missing packets in the denominator"


@pytest.mark.parametrize(
    "seqs,expected",
    [([10, 13, 11, 13], {"received": 4, "missing": 1, "loss_pct": 25.0, "longest_gap": 2}),
     ([10, 13, 12, 11, 13], {"received": 5, "missing": 0, "loss_pct": 0.0, "longest_gap": 2}),
     ([20, 23, 20, 23], {"received": 4, "missing": 2, "loss_pct": 50.0, "longest_gap": 2})],
)
def test_e4_repairs_duplicates_and_input_preservation(seqs: list[int], expected: dict[str, int | float]) -> None:
    original = seqs.copy()
    assert loss_report(seqs) == expected, "use arrival order, final missing count and historical longest gap"
    assert seqs == original, "a report must not change its capture"
    assert loss_report(seqs) == expected, "each report needs a fresh tracker"


@pytest.mark.parametrize("seqs", [[-1], [65536], [1, 3, -1], [65535, 65536]])
def test_e4_invalid_capture(seqs: list[int]) -> None:
    original = seqs.copy()
    with pytest.raises(ValueError):
        loss_report(seqs)
    assert seqs == original, "invalid captures must not be changed either"


def test_e4_fast_enough() -> None:
    seqs = [number % 65536 for number in range(500_000)]
    started = perf_counter()
    got = loss_report(seqs)
    elapsed = perf_counter() - started
    assert got == {"received": 500_000, "missing": 0, "loss_pct": 0.0, "longest_gap": 0}, "multiple full wraps must not create loss"
    assert elapsed <= 2.0, f"500,000 packets took {elapsed:.3f}s; keep recent history bounded and avoid capture rescans"
