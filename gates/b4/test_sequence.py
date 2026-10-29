"""Sequence gaps, recent duplicates, and delayed packets through the public API."""


def test_tracker_starts_empty_and_first_update_has_no_gap(telemetry):
    tracker = telemetry.SequenceTracker()
    assert (tracker.received, tracker.duplicates, tracker.out_of_order, tracker.missing) == (0, 0, 0, set())
    assert tracker.update(40000) == []
    assert (tracker.received, tracker.duplicates, tracker.out_of_order, tracker.missing) == (1, 0, 0, set())


def test_tracker_counts_consecutive_packets_without_gaps(telemetry):
    tracker = telemetry.SequenceTracker()
    for seq in (10, 11, 12):
        assert tracker.update(seq) == []
    assert tracker.received == 3
    assert tracker.missing == set()
    assert tracker.duplicates == tracker.out_of_order == 0


def test_tracker_returns_new_gaps_and_keeps_all_still_missing(telemetry):
    tracker = telemetry.SequenceTracker()
    tracker.update(10)
    assert tracker.update(13) == [11, 12]
    assert tracker.update(16) == [14, 15]
    assert tracker.missing == {11, 12, 14, 15}


def test_tracker_wraparound_is_consecutive_and_gaps_wrap_in_order(telemetry):
    tracker = telemetry.SequenceTracker()
    tracker.update(65534)
    assert tracker.update(65535) == []
    assert tracker.update(0) == []
    assert tracker.update(3) == [1, 2]
    assert tracker.missing == {1, 2}
    other = telemetry.SequenceTracker()
    other.update(65533)
    assert other.update(1) == [65534, 65535, 0]
    assert other.missing == {65534, 65535, 0}


def test_tracker_detects_immediate_and_recent_nonconsecutive_duplicates(telemetry):
    tracker = telemetry.SequenceTracker()
    tracker.update(100)
    assert tracker.update(100) == []
    tracker.update(103)
    assert tracker.update(100) == []
    assert tracker.duplicates == 2
    assert tracker.out_of_order == 0
    assert tracker.missing == {101, 102}
    assert tracker.update(104) == []


def test_tracker_late_packet_repairs_gap_without_moving_forward_position(telemetry):
    tracker = telemetry.SequenceTracker()
    tracker.update(10)
    tracker.update(14)
    assert tracker.update(12) == []
    assert tracker.missing == {11, 13}
    assert tracker.out_of_order == 1
    assert tracker.update(15) == []
    assert tracker.missing == {11, 13}
    assert tracker.update(12) == []
    assert tracker.duplicates == 1
    assert tracker.out_of_order == 1


def test_tracker_late_packet_without_known_gap_is_out_of_order(telemetry):
    tracker = telemetry.SequenceTracker()
    tracker.update(100)
    assert tracker.update(99) == []
    assert tracker.out_of_order == 1
    assert tracker.missing == set()
    assert tracker.update(101) == []


def test_tracker_late_packet_repairs_gap_across_wraparound(telemetry):
    tracker = telemetry.SequenceTracker()
    tracker.update(65533)
    tracker.update(1)
    assert tracker.update(65535) == []
    assert tracker.missing == {65534, 0}
    assert tracker.out_of_order == 1
    assert tracker.update(2) == []


def test_tracker_duplicate_history_covers_last_1024_and_expires_older_seen(telemetry):
    tracker = telemetry.SequenceTracker()
    for seq in range(1024):
        tracker.update(seq)
    assert tracker.update(0) == []
    assert tracker.duplicates == 1
    # A separate stream keeps the boundary independent of duplicate refresh policy.
    tracker = telemetry.SequenceTracker()
    for seq in range(1025):
        tracker.update(seq)
    assert tracker.update(0) == []
    assert tracker.duplicates == 0
    assert tracker.out_of_order == 1


def test_tracker_uses_half_range_rule_away_from_ambiguous_boundary(telemetry):
    tracker = telemetry.SequenceTracker()
    tracker.update(50000)
    assert tracker.update(17233) == []  # 32767 behind, despite a smaller raw integer.
    assert tracker.out_of_order == 1
    assert tracker.update(50001) == []
    forward = telemetry.SequenceTracker()
    forward.update(0)
    assert forward.update(32767) == list(range(1, 32767))
    assert forward.missing == set(range(1, 32767))
