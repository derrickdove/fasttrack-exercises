"""Station-log contracts; each E-number is one learner exercise."""
import copy
import csv
import json
from pathlib import Path

import pytest

from starter.logs import latest_per_channel, merge_logs, read_measurements, write_results

HEADER = "timestamp,channel,value,unit\n"


@pytest.fixture
def station_log(tmp_path: Path) -> Path:
    path = tmp_path / "station.csv"
    path.write_text(
        HEADER
        + "2026-01-02T09:00:03Z,bus_voltage,24.50,V\n"
        + "\n"
        + "2026-01-02T09:00:01Z,bus_voltage,24.0,V\n"
        + "2026-01-02T09:00:02Z,coil_current,0.32,A\n"
        + "2026-01-02T09:00:04Z,coil_current,0.34,A\n",
        encoding="utf-8",
    )
    return path


def test_e1_read_rows_in_file_order(station_log: Path) -> None:
    got = read_measurements(station_log)
    expected = [
        {"timestamp": "2026-01-02T09:00:03Z", "channel": "bus_voltage", "value": 24.5, "unit": "V"},
        {"timestamp": "2026-01-02T09:00:01Z", "channel": "bus_voltage", "value": 24.0, "unit": "V"},
        {"timestamp": "2026-01-02T09:00:02Z", "channel": "coil_current", "value": 0.32, "unit": "A"},
        {"timestamp": "2026-01-02T09:00:04Z", "channel": "coil_current", "value": 0.34, "unit": "A"},
    ]
    assert got == expected, f"Keep record order and skip blank lines; got {got!r}"
    assert all(isinstance(row["value"], float) for row in got), "Every value must be a float"


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
@pytest.mark.parametrize("as_string", [False, True])
def test_e1_quoted_fields_and_path_types(tmp_path: Path, ending: str, as_string: bool) -> None:
    path = tmp_path / "quoted.csv"
    text = HEADER + '2026-01-02T09:00:01Z,"rack, temp\u00e9rature",-2.5e1,\u00b0C\n'
    path.write_bytes(text.replace("\n", ending).encode("utf-8"))
    got = read_measurements(str(path) if as_string else path)
    assert got == [{
        "timestamp": "2026-01-02T09:00:01Z",
        "channel": "rack, temp\u00e9rature", "value": -25.0, "unit": "\u00b0C",
    }], f"CSV quoting and UTF-8 text must survive: {got!r}"


@pytest.mark.parametrize("blank_lines", ["", "\n\n"])
def test_e1_header_only(tmp_path: Path, blank_lines: str) -> None:
    path = tmp_path / "empty.csv"
    path.write_text(HEADER + blank_lines, encoding="utf-8")
    assert read_measurements(path) == [], "A header is not a measurement"


def test_e1_invalid_numeric_value(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(HEADER + "2026-01-02T09:00:01Z,bus_voltage,OVERLOAD,V\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_measurements(path)


def test_e1_missing_log(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_measurements(tmp_path / "missing.csv")


def test_e2_formatted_json_replaces_old_file(tmp_path: Path) -> None:
    path = tmp_path / "results.json"
    path.write_text("previous report must disappear" * 20, encoding="utf-8")
    results = [{"value": 24.5, "channel": "bus_voltage", "limits": {"upper": 25, "lower": 23}}]
    before = copy.deepcopy(results)
    returned = write_results(path, results)
    text = path.read_text(encoding="utf-8")
    assert returned is None, "Writing results returns None"
    assert json.loads(text) == results, "Write the entire result list"
    assert text in (json.dumps(results, indent=2, sort_keys=True),
                    json.dumps(results, indent=2, sort_keys=True) + "\n"), "Use indent=2 and sorted keys at every level"
    assert results == before, "Do not change the caller's data"


def test_e2_creates_parent_folders_and_accepts_string_path(tmp_path: Path) -> None:
    path = tmp_path / "reports" / "run-01" / "results.json"
    write_results(str(path), [{"channel": "bus_voltage", "passed": True}])
    assert path.is_file(), "Create every missing parent folder"
    assert json.loads(path.read_text(encoding="utf-8")) == [{"channel": "bus_voltage", "passed": True}]


def test_e2_empty_results(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    write_results(path, [])
    assert path.read_text(encoding="utf-8") in ("[]", "[]\n"), "Empty results are a JSON list"


def test_e2_unicode_and_json_value_types(tmp_path: Path) -> None:
    path = tmp_path / "operator.json"
    results = [{"operator": "Ren\u00e9e", "passed": False, "comment": None, "samples": [1, 2.5]}]
    write_results(path, results)
    assert json.loads(path.read_text(encoding="utf-8")) == results, "Preserve text, booleans, null and numbers"


def test_e3_newest_per_channel_not_last_row(station_log: Path) -> None:
    got = latest_per_channel(str(station_log))
    assert got == {"bus_voltage": 24.5, "coil_current": 0.34}, f"Choose timestamps per channel: {got!r}"
    assert all(isinstance(value, float) for value in got.values()), "Return numeric float values"


def test_e3_compares_full_date_and_time(tmp_path: Path) -> None:
    path = tmp_path / "overnight.csv"
    path.write_text(
        HEADER
        + "2026-02-01T00:00:01Z,bus_voltage,24.5,V\n"
        + "2026-01-31T23:59:59Z,bus_voltage,24.0,V\n"
        + "2025-12-31T23:59:59Z,bus_voltage,23.5,V\n",
        encoding="utf-8",
    )
    assert latest_per_channel(path) == {"bus_voltage": 24.5}, "Compare the date as well as the time"


def test_e3_later_row_wins_equal_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "ties.csv"
    path.write_text(
        HEADER
        + "2026-01-02T09:00:03Z,bus_voltage,24.5,V\n"
        + "2026-01-02T09:00:03Z,bus_voltage,24.7,V\n"
        + "\n"
        + "2026-01-02T09:00:01Z,bus_voltage,23.0,V\n",
        encoding="utf-8",
    )
    assert latest_per_channel(path) == {"bus_voltage": 24.7}, "Use the later tied row, then ignore older rows"


def test_e3_header_only(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text(HEADER + "\n", encoding="utf-8")
    assert latest_per_channel(path) == {}, "No measurements means no channel values"


@pytest.mark.parametrize("missing", [True, False])
def test_e3_read_errors_propagate(tmp_path: Path, missing: bool) -> None:
    path = tmp_path / "error.csv"
    if not missing:
        path.write_text(HEADER + "2026-01-02T09:00:01Z,bus_voltage,bad,V\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError if missing else ValueError):
        latest_per_channel(path)


def test_e4_sorted_merge_preserves_ties_and_field_text(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    out_path = tmp_path / "merged.csv"
    first.write_text(
        HEADER
        + "2026-01-02T09:00:03Z,last,3,V\n"
        + "2026-01-02T09:00:02Z,z_first_tie,024.500,V\n"
        + "\n"
        + "2026-01-02T09:00:02Z,a_second_tie,+2.45e1,V\n",
        encoding="utf-8",
    )
    second.write_text(
        HEADER
        + "2026-01-02T09:00:02Z,z_first_tie,024.500,V\n"
        + "2026-01-02T09:00:01Z,first,-0.0,A\n",
        encoding="utf-8",
    )
    out_path.write_text("old report" * 100, encoding="utf-8")
    originals = (first.read_bytes(), second.read_bytes())
    count = merge_logs([first, str(second)], str(out_path))
    with out_path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.reader(source))
    expected = [
        ["timestamp", "channel", "value", "unit"],
        ["2026-01-02T09:00:01Z", "first", "-0.0", "A"],
        ["2026-01-02T09:00:02Z", "z_first_tie", "024.500", "V"],
        ["2026-01-02T09:00:02Z", "a_second_tie", "+2.45e1", "V"],
        ["2026-01-02T09:00:02Z", "z_first_tie", "024.500", "V"],
        ["2026-01-02T09:00:03Z", "last", "3", "V"],
    ]
    assert rows == expected, f"Sort only by timestamp; preserve ties, duplicates and field spelling: {rows!r}"
    assert count == 5 and type(count) is int, f"Count only measurement rows, got {count!r}"
    assert (first.read_bytes(), second.read_bytes()) == originals, "Input logs must remain unchanged"


@pytest.mark.parametrize("input_count", [0, 2])
def test_e4_no_records_still_writes_header(tmp_path: Path, input_count: int) -> None:
    paths = []
    for index in range(input_count):
        path = tmp_path / f"empty-{index}.csv"
        path.write_text(HEADER + "\n", encoding="utf-8")
        paths.append(path)
    out_path = tmp_path / "merged.csv"
    count = merge_logs(paths, out_path)
    with out_path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.reader(source))
    assert count == 0, "Header-only inputs contribute no records"
    assert rows == [["timestamp", "channel", "value", "unit"]], "Even an empty merge has the standard header"


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_e4_quoted_unicode_fields(tmp_path: Path, ending: str) -> None:
    path = tmp_path / "temperature.csv"
    text = HEADER + '2026-01-02T09:00:01Z,"rack, temp\u00e9rature",002.50,\u00b0C\n'
    path.write_bytes(text.replace("\n", ending).encode("utf-8"))
    out_path = tmp_path / "merged.csv"
    count = merge_logs([str(path)], out_path)
    with out_path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.reader(source))
    assert count == 1
    assert rows[1] == ["2026-01-02T09:00:01Z", "rack, temp\u00e9rature", "002.50", "\u00b0C"], "Use CSV quoting and UTF-8"


def test_e4_sorts_across_date_boundary(tmp_path: Path) -> None:
    path = tmp_path / "overnight.csv"
    path.write_text(
        HEADER
        + "2026-02-01T00:00:01Z,bus_voltage,24.5,V\n"
        + "2026-01-31T23:59:59Z,bus_voltage,24.0,V\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "merged.csv"
    assert merge_logs([path], out_path) == 2
    with out_path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    assert [row["value"] for row in rows] == ["24.0", "24.5"], "Sort by the full timestamp"


def test_e4_missing_input(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        merge_logs([tmp_path / "missing.csv"], tmp_path / "merged.csv")
