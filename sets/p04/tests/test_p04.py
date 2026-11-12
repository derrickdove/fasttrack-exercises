import json
from pathlib import Path

import pytest

from starter.filesafe import (
    clean_lines,
    count_readings,
    file_details,
    labels_from_json,
    labels_to_json,
    optional_lines,
    read_csv,
    read_note,
    require_channel,
    traceback_answers,
    try_reading,
    write_lines,
)


def _traceback_choice_is_correct(question: str, choice: object) -> bool:
    return choice == {"Q1": "B", "Q2": "C", "Q3": "A"}[question]


def _message(call: str, expected: object, got: object) -> str:
    message = f"{call}: expected {expected!r}, got {got!r}."
    if got is None and expected is not None:
        message += " your function returned None: did you forget `return`?"
        message += " Printing a result does not return it."
    return message


@pytest.mark.parametrize("text", [" Ready\nCheck cable\n", "", "No final newline"])
def test_e1_reads_all_text(tmp_path: Path, text: str) -> None:
    path = tmp_path / "note.txt"
    path.write_text(text, encoding="utf-8")
    got = read_note(str(path))
    assert got == text, _message(f"read_note({str(path)!r})", text, got)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("  CH1 ready  \n\n CH2 ready\n", ["CH1 ready", "CH2 ready"]),
        ("", []),
        ("\n\n", []),
        ("5.0\n5.0", ["5.0", "5.0"]),
    ],
)
def test_e2_strips_and_skips_blanks(tmp_path: Path, text: str, expected: list[str]) -> None:
    path = tmp_path / "log.txt"
    path.write_text(text, encoding="utf-8")
    got = clean_lines(str(path))
    assert got == expected, _message(f"clean_lines({str(path)!r})", expected, got)


@pytest.mark.parametrize("lines", [["Connect meter", "Start run"], ["Stop run"], []])
def test_e3_creates_checklist(tmp_path: Path, lines: list[str]) -> None:
    path = tmp_path / "check.txt"
    before = lines.copy()
    got = write_lines(str(path), lines)
    call = f"write_lines({str(path)!r}, {before!r})"
    assert got is None, _message(call, None, got)
    assert path.exists(), (
        "Write through the opened file with its write method; print only shows text on screen. "
        + _message(call + " file exists", True, path.exists())
    )
    text = path.read_text(encoding="utf-8")
    expected = ""
    for line in before:
        expected += line + "\n"
    assert text == expected, _message(call + " saved text", expected, text)
    assert lines == before, _message(call + " input list after writing", before, lines)


@pytest.mark.parametrize("lines,expected", [(["New check"], "New check\n"), ([], "")])
def test_e3_replaces_old_text(tmp_path: Path, lines: list[str], expected: str) -> None:
    path = tmp_path / "check.txt"
    path.write_text("Old checklist\nAnother old line\n", encoding="utf-8")
    got = write_lines(str(path), lines)
    call = f"write_lines({str(path)!r}, {lines!r})"
    assert got is None, _message(call, None, got)
    text = path.read_text(encoding="utf-8")
    assert text == expected, _message(call + " replacement text", expected, text)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("channel,voltage\nCH1,2.5\nCH2,0\n",
         [{"channel": "CH1", "voltage": "2.5"}, {"channel": "CH2", "voltage": "0"}]),
        ("channel,voltage\n", []),
        ("operator,status\nLee,ready\n", [{"operator": "Lee", "status": "ready"}]),
    ],
)
def test_e4_reads_csv_rows(tmp_path: Path, text: str, expected: list[dict[str, str]]) -> None:
    path = tmp_path / "table.csv"
    path.write_text(text, encoding="utf-8")
    got = read_csv(str(path))
    assert got == expected, _message(f"read_csv({str(path)!r})", expected, got)


@pytest.mark.parametrize("text,expected", [("2.5", 2.5), ("0", 0.0), ("-1.25", -1.25)])
def test_e5_numeric_reading(text: str, expected: float) -> None:
    got = try_reading(text)
    call = f"try_reading({text!r})"
    assert isinstance(got, float), _message(call, f"float {expected}", got)
    assert got == expected, _message(call, expected, got)


@pytest.mark.parametrize("text", ["READY", "", "broken"])
def test_e5_invalid_reading_returns_none(text: str) -> None:
    got = try_reading(text)
    assert got is None, _message(f"try_reading({text!r})", None, got)


@pytest.mark.parametrize("channel", [1, 8, 12])
def test_e6_accepts_positive_channels(channel: int) -> None:
    got = require_channel(channel)
    assert got == channel, _message(f"require_channel({channel})", channel, got)


@pytest.mark.parametrize("channel", [0, -2, -7])
def test_e6_error_names_bad_channel(channel: int) -> None:
    call = f"require_channel({channel})"
    try:
        got = require_channel(channel)
    except ValueError as error:
        message = str(error)
        assert str(channel) in message, _message(call + " error message", f"text including {channel}", message)
    else:
        assert False, _message(call, f"ValueError with {channel} in its message", got)


@pytest.mark.parametrize("text,expected", [(" CH1 \n\nCH2\n", ["CH1", "CH2"]), ("", [])])
def test_e7_reads_present_log(tmp_path: Path, text: str, expected: list[str]) -> None:
    path = tmp_path / "log.txt"
    path.write_text(text, encoding="utf-8")
    got = optional_lines(str(path))
    assert got == expected, _message(f"optional_lines({str(path)!r})", expected, got)


def test_e7_missing_file_returns_empty_list(tmp_path: Path) -> None:
    path = tmp_path / "missing.txt"
    got = optional_lines(str(path))
    assert got == [], _message(f"optional_lines({str(path)!r})", [], got)
    assert not path.exists(), _message("optional_lines(missing file) file exists afterward", False, path.exists())


def test_e7_damaged_text_error_surfaces(tmp_path: Path) -> None:
    path = tmp_path / "damaged.txt"
    path.write_bytes(b"\xff\xfe")
    try:
        got = optional_lines(str(path))
    except UnicodeDecodeError:
        return
    else:
        assert False, _message(f"optional_lines({str(path)!r})", "UnicodeDecodeError from damaged UTF-8", got)


@pytest.mark.parametrize("labels", [{"bench": "B2"}, {}, {"operator": "Lee", "status": "ready"}])
def test_e8_encodes_dictionary_as_json(labels: dict[str, str]) -> None:
    got = labels_to_json(labels)
    call = f"labels_to_json({labels!r})"
    assert isinstance(got, str), _message(call, "JSON text as a string", got)
    try:
        restored = json.loads(got)
    except ValueError:
        assert False, _message(call, "valid JSON text", got)
    else:
        assert restored == labels, _message(call + " decoded content", labels, restored)


@pytest.mark.parametrize(
    "text,expected",
    [('{"operator": "Lee"}', {"operator": "Lee"}), ("{}", {}),
     ('{"status":"ready", "bench":"B2"}', {"status": "ready", "bench": "B2"})],
)
def test_e8_decodes_json_to_dictionary(text: str, expected: dict[str, str]) -> None:
    got = labels_from_json(text)
    assert got == expected, _message(f"labels_from_json({text!r})", expected, got)


def test_e8_round_trip() -> None:
    labels = {"bench": "C3", "operator": "Kai"}
    got = labels_from_json(labels_to_json(labels))
    assert got == labels, _message(f"labels_from_json(labels_to_json({labels!r}))", labels, got)


@pytest.mark.parametrize("name,present,suffix", [("run.txt", True, ".txt"), ("missing.json", False, ".json"), ("README", True, "")])
def test_e9_file_metadata(tmp_path: Path, name: str, present: bool, suffix: str) -> None:
    path = tmp_path / name
    if present:
        path.write_text("station note\n", encoding="utf-8")
    got = file_details(str(path))
    expected = {"name": name, "suffix": suffix, "exists": present}
    call = f"file_details({str(path)!r})"
    assert got == expected, _message(call, expected, got)
    assert isinstance(got["exists"], bool), _message(call + " exists value", f"bool {present}", got["exists"])
    assert path.exists() == present, _message(call + " file exists afterward", present, path.exists())


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2.5\nREADY\n0\n\n", {"good": 2, "bad": 1}),
        ("", {"good": 0, "bad": 0}),
        ("\n\n", {"good": 0, "bad": 0}),
        ("ERROR\nWAIT\n", {"good": 0, "bad": 2}),
        (" 3.5 \n-1.0\n3.5", {"good": 3, "bad": 0}),
        ("0\n0\nBAD\nBAD\n", {"good": 2, "bad": 2}),
    ],
)
def test_e10_counts_each_nonblank_line(tmp_path: Path, text: str, expected: dict[str, int]) -> None:
    path = tmp_path / "run.txt"
    path.write_text(text, encoding="utf-8")
    got = count_readings(str(path))
    assert got == expected, _message(f"count_readings({str(path)!r})", expected, got)


@pytest.mark.parametrize(
    "question,hint",
    [("Q1", "Revisit len(readings) and comparing lists with numbers."),
     ("Q2", "Revisit return versus print; follow the None value back to its helper."),
     ("Q3", "Revisit E5: numeric conversion and except ValueError.")],
    ids=["Q1", "Q2", "Q3"],
)
def test_e11_traceback_choices(question: str, hint: str) -> None:
    got = traceback_answers()
    call = "traceback_answers()"
    assert isinstance(got, dict), _message(call, "a dictionary with Q1, Q2, Q3 choices", got)
    assert set(got) == {"Q1", "Q2", "Q3"}, _message(call + " keys", ["Q1", "Q2", "Q3"], list(got))
    correct = _traceback_choice_is_correct(question, got.get(question))
    assert correct, _message(call + f"[{question!r}]", "the correct uppercase choice; " + hint, got.get(question))
