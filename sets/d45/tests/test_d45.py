from copy import deepcopy
from pathlib import Path
import time
import tomllib

import pytest

from starter.topology import (
    UUT_INSTRUMENTS,
    conflicts,
    instruments_for,
    load,
    setup_order,
    validate,
)


DATA = Path(__file__).resolve().parents[1] / "data" / "station.toml"


@pytest.fixture
def cfg():
    # Parse directly so E2 is independent of the learner's E1 implementation.
    with DATA.open("rb") as stream:
        return tomllib.load(stream)


def test_e1_load_example(cfg):
    assert load(DATA) == cfg, "load must return the TOML dictionary unchanged"
    assert load(str(DATA)) == cfg, "string paths and Path objects must both work"


def test_e1_load_empty_and_errors(tmp_path):
    empty = tmp_path / "empty station.toml"
    empty.write_text("", encoding="utf-8")
    assert load(empty) == {}, "empty TOML is an empty dictionary"
    with pytest.raises(FileNotFoundError):
        load(tmp_path / "missing.toml")
    broken = tmp_path / "broken.toml"
    broken.write_text("instruments = [", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        load(broken)


def test_e1_valid_and_empty(cfg):
    original = deepcopy(cfg)
    assert validate(cfg) == [], "separate PSU channels and shared meters are valid"
    assert cfg == original, "validation must not modify the configuration"
    assert validate({}) == []
    assert validate({"uuts": [{"id": "unused", "instruments": []}]}) == []
    # Id namespaces are separate, and repeated references are harmless.
    cfg["uuts"][0]["id"] = "psu-a"
    cfg["uuts"][0]["instruments"].append("psu-a")
    assert validate(cfg) == []


def test_e1_duplicate_ids_and_resources(cfg):
    cfg["instruments"].extend([deepcopy(cfg["instruments"][0])] * 2)
    cfg["uuts"].extend([deepcopy(cfg["uuts"][0])] * 2)
    expected = [
        "duplicate instrument id: psu-a",
        "duplicate resource: supply-01/channel/1",
        "duplicate uut id: uut-a",
    ]
    assert validate(cfg) == expected, "duplicates must produce one message per value"
    cfg["instruments"] = [
        {"id": "one", "kind": "scope", "resource": "same-port"},
        {"id": "two", "kind": "dmm", "resource": "same-port"},
    ]
    cfg["uuts"] = []
    assert validate(cfg) == ["duplicate resource: same-port"]


def test_e1_unknown_references_and_shared_psu(cfg):
    cfg["uuts"][1]["instruments"].extend(["psu-a", "missing", "missing"])
    cfg["uuts"][2]["instruments"].append("psu-a")
    cfg["uuts"][0]["instruments"].append("DMM")
    expected = [
        "shared psu channel: psu-a -> uut-a, uut-b, uut-c",
        "unknown instrument: uut-a -> DMM",
        "unknown instrument: uut-b -> missing",
    ]
    original = deepcopy(cfg)
    assert validate(cfg) == expected, "report every problem in alphabetical order"
    assert cfg == original
    assert validate({"uuts": [{"id": "empty-rack", "instruments": ["x"]}]}) == [
        "unknown instrument: empty-rack -> x"
    ]


def test_e1_first_instrument_kind_and_all_uut_records(cfg):
    cfg["instruments"].append(
        {"id": "psu-a", "kind": "dmm", "resource": "meter-01"}
    )
    cfg["uuts"].append({"id": "uut-b", "instruments": ["psu-a", "gone"]})
    expected = [
        "duplicate instrument id: psu-a",
        "duplicate resource: meter-01",
        "duplicate uut id: uut-b",
        "shared psu channel: psu-a -> uut-a, uut-b",
        "unknown instrument: uut-b -> gone",
    ]
    assert validate(cfg) == expected, "use the first kind, but inspect every record"


@pytest.mark.parametrize("uut, expected", [
    ("uut-a", ["dmm", "psu-a"]),
    ("uut-b", ["dmm", "psu-b"]),
    ("uut-c", ["scope"]),
    ("uut-d", ["dmm", "scope"]),
])
def test_e2_instrument_ids(cfg, uut, expected):
    assert instruments_for(cfg, uut) == expected


def test_e2_empty_and_repeated_references(cfg):
    cfg["uuts"].append({"id": "spare", "instruments": []})
    cfg["uuts"][0]["instruments"] = ["psu-a", "dmm", "dmm"]
    assert instruments_for(cfg, "spare") == []
    assert instruments_for(cfg, "uut-a") == ["dmm", "psu-a"]


@pytest.mark.parametrize("empty", [False, True])
def test_e2_missing_uut(cfg, empty):
    with pytest.raises(KeyError) as caught:
        instruments_for({} if empty else cfg, "unknown-rack")
    assert caught.value.args == ("unknown-rack",)


def test_e2_returns_fresh_list_without_mutation(cfg):
    original = deepcopy(cfg)
    result = instruments_for(cfg, "uut-a")
    result.append("operator-note")
    assert cfg == original, "the returned list must not alias configuration data"
    assert instruments_for(cfg, "uut-a") == ["dmm", "psu-a"]


@pytest.mark.parametrize("deps, expected", [
    ({}, []),
    ({"scope": ["trigger"], "dmm": []}, ["dmm", "trigger", "scope"]),
    ({"scope": [], "dmm": [], "psu": []}, ["dmm", "psu", "scope"]),
    ({"scope": ["psu", "trigger"], "trigger": ["psu"], "psu": []},
     ["psu", "trigger", "scope"]),
])
def test_e3_station_setup_order(deps, expected):
    assert setup_order(deps) == expected, "prerequisites must be ready first"


def test_e3_newly_ready_instrument_wins_alphabetical_tie():
    deps = {"z-scope": [], "a-dmm": ["b-psu"], "b-psu": []}
    assert setup_order(deps) == ["b-psu", "a-dmm", "z-scope"], (
        "choose from all ready instruments after each removal"
    )


def test_e3_value_only_ids_repeated_edges_and_no_mutation():
    deps = {"scope": ["trigger", "trigger"], "dmm": ["psu"]}
    original = deepcopy(deps)
    assert setup_order(deps) == ["psu", "dmm", "trigger", "scope"]
    assert deps == original, "do not remove edges from the caller's dictionary"


@pytest.mark.parametrize("deps", [
    {"psu": ["psu"]},
    {"psu": ["relay"], "relay": ["psu"]},
    {"a-blocked": ["psu"], "psu": ["relay"], "relay": ["psu"], "dmm": []},
    {"scope": ["trigger"], "trigger": ["relay"], "relay": ["scope"],
     "a-blocked": ["scope"], "psu": []},
    {"psu": ["relay"], "relay": ["psu"], "scope": ["trigger"],
     "trigger": ["scope"]},
])
def test_e3_cycle_names_a_real_closed_path(deps):
    original = deepcopy(deps)
    with pytest.raises(ValueError) as caught:
        setup_order(deps)
    message = str(caught.value)
    assert message.startswith("cycle: "), "explain that setup contains a cycle"
    path = message.removeprefix("cycle: ").split(" -> ")
    assert len(path) >= 2 and path[0] == path[-1], "name a closed path"
    assert len(set(path[:-1])) == len(path) - 1, "omit any tail before the cycle"
    for node, prerequisite in zip(path, path[1:]):
        assert prerequisite in deps.get(node, []), (
            f"{node} does not depend on {prerequisite}; name actual cycle edges"
        )
    with pytest.raises(ValueError) as again:
        setup_order(deps)
    assert str(again.value) == message, "cycle reporting must be deterministic"
    assert deps == original


@pytest.mark.parametrize("schedule, expected", [
    ([], []),
    ([("uut-a", 0, 4)], []),
    ([("uut-b", 2, 6), ("uut-a", 0, 3), ("uut-c", 1, 9)],
     [("uut-a", "uut-b")]),
    ([("uut-a", 0, 4), ("uut-b", 4, 9)], []),
    ([("uut-a", -4, 0), ("uut-b", -3, -1)], [("uut-a", "uut-b")]),
    ([("uut-a", 0, 9), ("uut-c", 0, 9)], []),
    ([("uut-c", 1, 5), ("uut-d", 1, 5)], [("uut-c", "uut-d")]),
])
def test_e4_shared_instruments_and_half_open_windows(schedule, expected):
    assert conflicts(schedule) == expected, (
        "only overlapping windows on a shared instrument conflict"
    )


def test_e4_keep_longest_window_and_ignore_same_uut():
    schedule = [("uut-a", 0, 100), ("uut-a", 1, 2), ("uut-b", 50, 60)]
    assert conflicts(schedule) == [("uut-a", "uut-b")], (
        "a shorter later window must not hide an outstanding long window"
    )
    assert conflicts([("uut-a", 0, 10), ("uut-a", 1, 9)]) == []


def test_e4_unique_sorted_pairs_and_no_mutation():
    schedule = [("uut-d", 1, 9), ("uut-c", 1, 9), ("uut-b", 1, 9),
                ("uut-a", 1, 9), ("uut-d", 2, 8), ("uut-b", 3, 7)]
    original = list(schedule)
    wiring = deepcopy(UUT_INSTRUMENTS)
    expected = [("uut-a", "uut-b"), ("uut-a", "uut-d"),
                ("uut-b", "uut-d"), ("uut-c", "uut-d")]
    assert conflicts(schedule) == expected, "sort pairs and remove repeated reports"
    assert schedule == original, "sort a copy rather than the caller's schedule"
    assert UUT_INSTRUMENTS == wiring, "the supplied station wiring must stay intact"


@pytest.mark.parametrize("schedule, error, args", [
    ([("missing", 0, 1)], KeyError, ("missing",)),
    ([("uut-a", 3, 3)], ValueError, ("invalid window: uut-a",)),
    ([("uut-b", 4, 1)], ValueError, ("invalid window: uut-b",)),
    ([("missing", 4, 1)], KeyError, ("missing",)),
    ([("uut-b", 5, 5), ("missing", 0, 1)], ValueError,
     ("invalid window: uut-b",)),
    ([("missing", 5, 6), ("uut-a", 0, 0)], KeyError, ("missing",)),
])
def test_e4_errors_follow_input_order(schedule, error, args):
    with pytest.raises(error) as caught:
        conflicts(schedule)
    assert caught.value.args == args, "identify the first invalid input record"


def test_e4_sweep_matches_small_pairwise_check():
    # A deliberately small, independent all-pairs check verifies mixed windows.
    uuts = ["uut-a", "uut-b", "uut-c", "uut-d"]
    schedule = [(uuts[i % 4], (i * 7) % 29 - 14,
                 (i * 7) % 29 - 14 + i % 9 + 1) for i in range(40)]
    expected = set()
    for index, (uut, start, end) in enumerate(schedule):
        for other, other_start, other_end in schedule[index + 1:]:
            shared = set(UUT_INSTRUMENTS[uut]) & set(UUT_INSTRUMENTS[other])
            if uut != other and shared and max(start, other_start) < min(end, other_end):
                expected.add((min(uut, other), max(uut, other)))
    assert conflicts(schedule) == sorted(expected)


def test_e4_fast_enough():
    # Many simultaneously active windows make a window-by-window sweep quadratic.
    uuts = ["uut-a", "uut-b", "uut-c", "uut-d"]
    schedule = [(uuts[i % 4], i, 100_000) for i in reversed(range(80_000))]
    started = time.perf_counter()
    got = conflicts(schedule)
    elapsed = time.perf_counter() - started
    assert got == [("uut-a", "uut-b"), ("uut-a", "uut-d"),
                   ("uut-b", "uut-d"), ("uut-c", "uut-d")]
    assert elapsed <= 2.0, f"80,000 windows took {elapsed:.3f}s; use sort + sweep"
