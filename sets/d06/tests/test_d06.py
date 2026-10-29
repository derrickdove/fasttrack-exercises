"""Pass/fail checks for the station's result models."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from enum import Enum
from itertools import permutations
from time import perf_counter
import tracemalloc

import pytest

from starter.models import ChannelBank, Reading, RunningStats, Status, worst


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([Status.PASS], Status.PASS),
        ([Status.PASS, Status.PASS], Status.PASS),
        ([Status.FAIL], Status.FAIL),
        ([Status.PASS, Status.FAIL, Status.PASS], Status.FAIL),
        ([Status.ERROR], Status.ERROR),
    ],
)
def test_e1_worst_outcome(statuses, expected):
    assert worst(statuses) is expected, "Return the most severe Status member"
    assert issubclass(Status, Enum), "Status must be an enum"
    assert set(Status.__members__) == {"PASS", "FAIL", "ERROR"}
    assert len(set(Status)) == 3, "Outcomes must be three distinct members"


def test_e1_order_does_not_change_severity():
    for outcomes in permutations([Status.PASS, Status.FAIL, Status.ERROR]):
        assert worst(outcomes) is Status.ERROR, f"ERROR must win for {outcomes}"


@pytest.mark.parametrize("statuses", [[], (), iter(())])
def test_e1_empty_means_error(statuses):
    assert worst(statuses) is Status.ERROR, "No checks is an ERROR, never a PASS"


def test_e1_accepts_single_use_iterables():
    outcomes = (status for status in [Status.PASS, Status.FAIL, Status.PASS])
    assert worst(outcomes) is Status.FAIL, "A generator can be consumed only once"


def test_e2_frozen_dataclass_preserves_fields():
    reading = Reading(" supply ", -0.25, "V")
    assert is_dataclass(reading), "Reading must be a dataclass"
    assert [field.name for field in fields(reading)] == ["channel", "value", "unit"]
    assert reading.channel == " supply ", "Preserve a non-empty channel exactly"
    assert reading.value == -0.25
    assert reading.unit == "V"
    assert reading == Reading(" supply ", -0.25, "V"), "Equal fields mean equal readings"
    with pytest.raises(FrozenInstanceError):
        reading.value = 1.0


@pytest.mark.parametrize(
    ("channel", "value"),
    [("", 1.0), ("supply", float("nan")), ("supply", float("inf")), ("supply", -float("inf"))],
)
def test_e2_rejects_invalid_readings(channel, value):
    with pytest.raises(ValueError):
        Reading(channel, value, "V")


@pytest.mark.parametrize(
    ("source", "value", "target", "expected"),
    [("V", 1.25, "mV", 1250.0), ("mV", -250.0, "V", -0.25),
     ("A", 0.012, "mA", 12.0), ("mA", 3.0, "A", 0.003),
     ("V", 0.0, "mV", 0.0)],
)
def test_e2_converts_supported_pairs(source, value, target, expected):
    original = Reading("supply", value, source)
    converted = original.to_unit(target)
    assert isinstance(converted, Reading), "Conversion returns a Reading"
    assert converted.channel == original.channel
    assert converted.unit == target
    assert converted.value == pytest.approx(expected)
    assert (original.value, original.unit) == (value, source), "Do not mutate the source"


@pytest.mark.parametrize("unit", ["V", "mV", "A", "mA"])
def test_e2_same_unit_returns_new_equal_reading(unit):
    original = Reading("load", 2.0, unit)
    converted = original.to_unit(unit)
    assert converted == original
    assert converted is not original, "Return a new Reading even for the same unit"


@pytest.mark.parametrize(
    ("source", "target"),
    [("V", "A"), ("mA", "mV"), ("A", "V"), ("mV", "mA"),
     ("V", "v"), ("V", "ohm"), ("ohm", "V"), ("ohm", "ohm"), ("", "V")],
)
def test_e2_rejects_unsupported_conversions(source, target):
    original = Reading("load", 1.0, source)
    assert original.unit == source, "Construction does not validate the unit"
    with pytest.raises(ValueError):
        original.to_unit(target)


def test_e2_conversion_cannot_create_infinity():
    original = Reading("supply", 1e308, "V")
    with pytest.raises(ValueError):
        original.to_unit("mV")


def test_e3_empty_statistics():
    stats = RunningStats()
    assert stats.count == 0
    for name in ("mean", "min", "max"):
        with pytest.raises(ValueError):
            getattr(stats, name)


@pytest.mark.parametrize(
    "values", [[-2.5], [0.0, 0.0, 0.0], [-4.0, -2.0, -6.0], [2.0, -1.0, 9.0, 2.0]],
)
def test_e3_statistics_after_each_add(values):
    stats = RunningStats()
    seen = []
    for value in values:
        assert stats.add(value) is None, "add updates the object and returns None"
        seen.append(value)
        assert stats.count == len(seen)
        assert stats.mean == pytest.approx(sum(seen) / len(seen))
        assert stats.min == min(seen)
        assert stats.max == max(seen)


def test_e3_instances_do_not_share_samples():
    voltage = RunningStats()
    current = RunningStats()
    voltage.add(12.0)
    current.add(0.5)
    voltage.add(10.0)
    assert (voltage.count, voltage.mean) == (2, 11.0)
    assert (current.count, current.mean) == (1, 0.5)


def test_e3_properties_are_read_only():
    stats = RunningStats()
    stats.add(3.0)
    for name in ("count", "mean", "min", "max"):
        with pytest.raises(AttributeError):
            setattr(stats, name, 99)


def test_e3_fast_enough():
    stats = RunningStats()
    started = perf_counter()
    for index in range(200_000):
        stats.add(float(index % 100))
        _ = stats.mean, stats.min, stats.max
        if index % 2048 == 0:
            assert perf_counter() - started < 2.0, "Keep add and property reads O(1)"
    elapsed = perf_counter() - started
    assert elapsed < 2.0, f"200,000 updates and property reads took {elapsed:.3f}s; limit 2s"
    assert (stats.count, stats.min, stats.max) == (200_000, 0.0, 99.0)
    assert stats.mean == pytest.approx(49.5)


def test_e3_constant_storage():
    # Trace retained memory separately so tracing cannot affect the speed check.
    tracemalloc.start()
    try:
        stats = RunningStats()
        for index in range(1_000):
            stats.add(float(index))
        before = tracemalloc.get_traced_memory()[0]
        for index in range(200_000):
            stats.add(float(index))
        growth = tracemalloc.get_traced_memory()[0] - before
    finally:
        tracemalloc.stop()
    # A retained list of these samples grows by several MB; aggregates need very little.
    assert growth < 256 * 1024, (
        f"Statistics storage grew by {growth:,} bytes; keep aggregates, not sample history"
    )


@pytest.fixture
def station_samples():
    return [("supply", 12.0, "V"), ("load", 0.5, "A"), ("supply", 10.0, "V")]


def test_e4_empty_bank():
    bank = ChannelBank()
    assert len(bank) == 0, "len counts distinct channels"
    assert bank.summary() == {}


def test_e4_interleaved_channels(station_samples):
    bank = ChannelBank()
    for channel, value, unit in station_samples:
        assert bank.add(Reading(channel, value, unit)) is None
    assert len(bank) == 2, "Three readings belong to two channels"
    assert bank.summary() == {
        "supply": {"unit": "V", "count": 2, "mean": 11.0, "min": 10.0, "max": 12.0},
        "load": {"unit": "A", "count": 1, "mean": 0.5, "min": 0.5, "max": 0.5},
    }
    bank.add(Reading("sensor", -2.0, "degC"))
    assert len(bank) == 3
    assert bank.summary()["sensor"] == {
        "unit": "degC", "count": 1, "mean": -2.0, "min": -2.0, "max": -2.0,
    }, "A bank can group any unit label when it stays the same per channel"


@pytest.mark.parametrize("changed_unit", ["mV", "A", "v", ""])
def test_e4_unit_mismatch_leaves_bank_unchanged(changed_unit):
    bank = ChannelBank()
    bank.add(Reading("supply", 12.0, "V"))
    before = bank.summary()
    with pytest.raises(ValueError):
        bank.add(Reading("supply", 999.0, changed_unit))
    assert bank.summary() == before, "Rejected readings must not affect any statistics"
    assert len(bank) == 1
    bank.add(Reading("supply", 10.0, "V"))
    assert bank.summary()["supply"]["mean"] == 11.0


def test_e4_summary_is_detached(station_samples):
    bank = ChannelBank()
    for channel, value, unit in station_samples:
        bank.add(Reading(channel, value, unit))
    snapshot = bank.summary()
    snapshot["supply"]["mean"] = 999.0
    del snapshot["load"]
    assert bank.summary()["supply"]["mean"] == 11.0, "Nested dictionaries must be fresh"
    assert len(bank) == 2
    earlier = bank.summary()
    bank.add(Reading("supply", 8.0, "V"))
    assert earlier["supply"]["count"] == 2, "Later adds must not change older summaries"
    assert bank.summary()["supply"]["mean"] == 10.0


def test_e4_banks_have_independent_state():
    first = ChannelBank()
    second = ChannelBank()
    first.add(Reading("supply", 12.0, "V"))
    assert len(second) == 0
    second.add(Reading("supply", 250.0, "mV"))
    assert first.summary()["supply"]["unit"] == "V"
    assert second.summary()["supply"]["unit"] == "mV"
