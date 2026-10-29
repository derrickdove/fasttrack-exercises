from time import perf_counter

import pytest

from starter.channels import (
    channel_stats,
    duplicate_serials,
    group_by_channel,
    missing_channels,
)


@pytest.mark.parametrize(
    ("readings", "expected"),
    [
        ([], {}),
        ([("BUS_V", 28.0)], {"BUS_V": [28.0]}),
        (
            [("BUS_V", 28.0), ("TEMP_C", -2.0), ("BUS_V", 27.9),
             ("TEMP_C", 0.0), ("BUS_V", 28.0)],
            {"BUS_V": [28.0, 27.9, 28.0], "TEMP_C": [-2.0, 0.0]},
        ),
    ],
)
def test_e1_groups_in_measurement_order(readings, expected):
    got = group_by_channel(readings)
    assert got == expected, f"for readings {readings!r}, expected {expected!r}, got {got!r}"


def test_e1_names_match_exactly():
    readings = [("BUS_V", 28.0), ("bus_v", 27.0), ("BUS_V ", 26.0)]
    expected = {"BUS_V": [28.0], "bus_v": [27.0], "BUS_V ": [26.0]}
    assert group_by_channel(readings) == expected, "Keep distinct channel spellings separate"


def test_e1_inputs_and_channel_lists_are_independent():
    readings = [("BUS_V", 28.0), ("TEMP_C", 21.0), ("BUS_V", 27.9)]
    original = readings.copy()
    got = group_by_channel(readings)
    assert readings == original, "Grouping must not change the supplied readings"
    got["BUS_V"].append(99.0)
    assert got["TEMP_C"] == [21.0], "Each channel needs its own value list"
    assert group_by_channel(readings)["BUS_V"] == [28.0, 27.9], "Calls need fresh results"


@pytest.mark.parametrize(
    ("readings", "expected"),
    [
        ([], {}),
        ([("BUS_V", 28.0)], {"BUS_V": (28.0, 28.0, 28.0)}),
        (
            [("BUS_V", 29.0), ("TEMP_C", -5.0), ("BUS_V", 27.0),
             ("TEMP_C", 0.0), ("BUS_V", 28.0)],
            {"BUS_V": (27.0, 29.0, 28.0), "TEMP_C": (-5.0, 0.0, -2.5)},
        ),
    ],
)
def test_e2_channel_summary(readings, expected):
    got = channel_stats(readings)
    assert got == expected, f"expected per-channel (min, max, mean) {expected!r}, got {got!r}"
    assert all(isinstance(stats, tuple) for stats in got.values()), "Return statistic tuples"


def test_e2_mean_counts_repeated_readings_without_rounding():
    readings = [("CURR_A", 0.1), ("CURR_A", 0.1), ("CURR_A", 0.8)]
    got = channel_stats(readings)
    assert set(got) == {"CURR_A"}, "Summarize exactly the channels present"
    assert isinstance(got["CURR_A"], tuple), "Return (min, max, mean) as a tuple"
    assert got["CURR_A"] == pytest.approx((0.1, 0.8, 1.0 / 3.0)), "Count every reading; do not round"


def test_e2_names_and_input_preserved():
    readings = [("TEMP_C", -1.0), ("temp_c", 9.0), ("TEMP_C", -3.0)]
    original = readings.copy()
    got = channel_stats(readings)
    assert got == {"TEMP_C": (-3.0, -1.0, -2.0), "temp_c": (9.0, 9.0, 9.0)}, "Names match exactly"
    assert readings == original, "Statistics must not reorder or change the readings"


@pytest.mark.parametrize(
    ("expected", "seen", "missing"),
    [
        ([], [], []),
        ([], ["AUX_V"], []),
        (["TEMP_C", "BUS_V", "TEMP_C"], [], ["BUS_V", "TEMP_C"]),
        (["TEMP_C", "BUS_V"], ["BUS_V", "TEMP_C", "BUS_V"], []),
        (["TEMP_C", "BUS_V", "CURR_A", "TEMP_C"],
         ["BUS_V", "BUS_V", "AUX_V"], ["CURR_A", "TEMP_C"]),
    ],
)
def test_e3_missing_unique_sorted(expected, seen, missing):
    got = missing_channels(expected, seen)
    assert got == missing, f"expected={expected!r}, seen={seen!r}: wanted {missing!r}, got {got!r}"


def test_e3_exact_names_and_string_sort_order():
    expected = ["ch2", "CH2", "CH10", "CH1", "CH2 "]
    got = missing_channels(expected, ["CH2", "unused"])
    assert got == ["CH1", "CH10", "CH2 ", "ch2"], "Use exact membership and normal string sorting"


def test_e3_inputs_unchanged():
    expected = ["TEMP_C", "BUS_V", "TEMP_C"]
    seen = ["BUS_V", "AUX_V", "BUS_V"]
    original_expected, original_seen = expected.copy(), seen.copy()
    got = missing_channels(expected, seen)
    assert got == ["TEMP_C"], "Report the missing channel once"
    assert expected == original_expected and seen == original_seen, "Do not change either list"


def test_e3_fast_enough():
    expected = [f"CH{index:06d}" for index in range(200_000)]
    seen = [f"CH{index:06d}" for index in range(100_000, 300_000)]
    wanted = expected[:100_000]
    started = perf_counter()
    got = missing_channels(expected, seen)
    elapsed = perf_counter() - started
    assert got == wanted, "Return the 100,000 missing channel names in sorted order"
    assert elapsed <= 2.0, f"Lookup took {elapsed:.3f}s; build a set once (limit 2s)"


@pytest.mark.parametrize(
    ("serials", "expected"),
    [
        ([], []),
        (["SN-1", "SN-2", "SN-3"], []),
        (["sn-1", "SN-1"], ["SN-1"]),
        (["sn-1", "SN-1", "Sn-1", "sN-1"], ["SN-1"]),
    ],
)
def test_e4_duplicates_once_in_uppercase(serials, expected):
    got = duplicate_serials(serials)
    assert got == expected, f"for serials {serials!r}, expected {expected!r}, got {got!r}"


def test_e4_order_is_second_appearance():
    serials = ["a-1", "z-2", "Z-2", "b-3", "B-3", "A-1", "z-2", "b-3"]
    assert duplicate_serials(serials) == ["Z-2", "B-3", "A-1"], "Report in order of second appearance"


def test_e4_keep_spaces_hyphens_and_digits():
    serials = ["sn-1", "SN1", "SN-01", " sn-1", "sn-1 ",
               "SN1", " SN-1", "SN-1 "]
    expected = ["SN1", " SN-1", "SN-1 "]
    assert duplicate_serials(serials) == expected, "Only normalize case, keeping spaces, hyphens, and digits"


def test_e4_input_and_calls_are_independent():
    serials = ["sn-2", "sn-1", "SN-2"]
    original = serials.copy()
    got = duplicate_serials(serials)
    assert got == ["SN-2"], "Recognize a later occurrence with different case"
    assert serials == original, "Do not uppercase or reorder the input list"
    assert duplicate_serials(["sn-2"]) == [], "Do not carry seen serials between calls"
