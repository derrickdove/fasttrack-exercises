from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from starter.review1 import (
    Instrument,
    Measurement,
    RowError,
    Status,
    classify,
    load_measurements,
    read_inventory,
    write_summary,
)

DATA = Path(__file__).resolve().parents[1] / "data"
HEADER = "channel,value,unit,low,high\n"


@pytest.fixture
def measurement_csv(tmp_path: Path) -> Path:
    path = tmp_path / "station readings.csv"
    path.write_bytes((DATA / "readings.csv").read_bytes())
    return path


def test_e1_inventory_file() -> None:
    got = read_inventory(DATA / "inventory.txt")
    expected = [
        Instrument("KEYSIGHT TECHNOLOGIES", "34461A", "MY57212345", "A.03.01"),
        Instrument("Rigol", "DP832", "SN-02", "1.2"),
    ]
    assert got == expected, "keep file order, trim fields, and skip blank lines"
    with pytest.raises(FrozenInstanceError):
        got[0].model = "changed"


@pytest.mark.parametrize("text", ["", "\n \t\n"])
def test_e1_empty_inventory(tmp_path: Path, text: str) -> None:
    path = tmp_path / "empty.txt"
    path.write_text(text, encoding="utf-8")
    assert read_inventory(path) == [], "an empty inventory has no instruments"


def test_e1_duplicates_and_unicode(tmp_path: Path) -> None:
    path = tmp_path / "inventory.txt"
    path.write_bytes("Métrix,M1,SN1,1.0\r\nMétrix,M1,SN1,1.0\r\n".encode("utf-8"))
    instrument = Instrument("Métrix", "M1", "SN1", "1.0")
    assert read_inventory(path) == [instrument, instrument], "do not deduplicate replies"


@pytest.mark.parametrize("bad", ["M,MODEL,SN", "M,MODEL,SN,1,extra", "M, ,SN,1", ",MODEL,SN,1"])
def test_e1_bad_reply_reports_line(tmp_path: Path, bad: str) -> None:
    path = tmp_path / "bad.txt"
    path.write_text("M,MODEL,SN,1\n\n" + bad, encoding="utf-8")
    with pytest.raises(ValueError, match="^line 3: expected four nonempty fields$"):
        read_inventory(path)


def test_e1_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_inventory(tmp_path / "missing.txt")


def test_e2_row_error_attributes() -> None:
    error = RowError(7, "invalid number")
    assert isinstance(error, ValueError), "RowError must be catchable as ValueError"
    assert error.line_number == 7, "save the physical file line for the operator"
    assert error.reason == "invalid number", "save the reason unchanged"
    assert error.args == (7, "invalid number"), "initialize ValueError with both arguments"


@pytest.mark.parametrize("line,reason", [(1, "bad header"), (12, "non-finite number"), (3, "")])
def test_e2_row_error_message(line: int, reason: str) -> None:
    error = RowError(line, reason)
    assert str(error) == f"line {line}: {reason}", "use the exact operator message format"


def test_e2_raise_and_catch() -> None:
    error = RowError(4, "reversed limits")
    with pytest.raises(ValueError) as caught:
        raise error
    assert caught.value is error, "catching a row error must preserve the exception object"


def test_e3_load_supplied_file(measurement_csv: Path) -> None:
    got = load_measurements(measurement_csv)
    expected = [
        Measurement("BUS", 28.0, "V", 27.0, 29.0),
        Measurement("BUS", 26.9, "V", 27.0, 29.0),
        Measurement("RETURN", 0.0, "A", None, 0.0),
        Measurement("sense,aux", 0.0025, "A", 0.0, None),
    ]
    assert got == expected, "parse numbers and quoted channels without losing file order"
    with pytest.raises(FrozenInstanceError):
        got[0].value = 99.0


@pytest.mark.parametrize("body", ["", "\n \t\n", "  CH1  , +1e-3 , mA , , \n"])
def test_e3_empty_and_trimmed_records(tmp_path: Path, body: str) -> None:
    path = tmp_path / "readings.csv"
    path.write_bytes((HEADER + body).replace("\n", "\r\n").encode("utf-8"))
    expected = [Measurement("CH1", 0.001, "mA", None, None)] if "CH1" in body else []
    assert load_measurements(path) == expected, "trim cells and support Windows line endings"


@pytest.mark.parametrize("text", ["", "channel,value,unit,high,low\n", " channel,value,unit,low,high\n", "\n" + HEADER])
def test_e3_bad_header(tmp_path: Path, text: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(RowError) as caught:
        load_measurements(path)
    assert (caught.value.line_number, caught.value.reason) == (1, "bad header")


@pytest.mark.parametrize(
    "row,reason",
    [
        ('""', "expected 5 fields"),
        ('"   "', "expected 5 fields"),
        ("BUS,28,V,27", "expected 5 fields"),
        ("BUS,28,V,27,29,extra", "expected 5 fields"),
        (",28,V,27,29", "empty channel or unit"),
        ("BUS,28, ,27,29", "empty channel or unit"),
        ("BUS,,V,27,29", "invalid number"),
        ("BUS,nope,V,27,29", "invalid number"),
        ("BUS,28,V,nope,29", "invalid number"),
        ("BUS,28,V,27,nope", "invalid number"),
        ("BUS,nan,V,27,29", "non-finite number"),
        ("BUS,28,V,-inf,29", "non-finite number"),
        ("BUS,28,V,27,1e999", "non-finite number"),
        ("BUS,28,V,29,27", "reversed limits"),
        (",oops,,99,1", "empty channel or unit"),
        ("BUS,inf,V,99,1", "non-finite number"),
    ],
)
def test_e3_bad_record_line_and_reason(tmp_path: Path, row: str, reason: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(HEADER + "BUS,28,V,27,29\n\n" + row + "\n", encoding="utf-8")
    with pytest.raises(RowError) as caught:
        load_measurements(path)
    assert caught.value.line_number == 4, "blank physical lines still count in errors"
    assert caught.value.reason == reason, "use the documented validation order and reason"
    assert str(caught.value) == f"line 4: {reason}"


def test_e3_first_bad_row(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(HEADER + "BUS,bad,V,0,1\nBUS,inf,V,0,1\n", encoding="utf-8")
    with pytest.raises(RowError) as caught:
        load_measurements(path)
    assert (caught.value.line_number, caught.value.reason) == (2, "invalid number")


def test_e3_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_measurements(tmp_path / "missing.csv")


@pytest.mark.parametrize(
    "value,low,high,expected",
    [(27.0, 27.0, 29.0, Status.PASS), (29.0, 27.0, 29.0, Status.PASS),
     (28.0, 27.0, 29.0, Status.PASS), (26.9, 27.0, 29.0, Status.LOW),
     (29.1, 27.0, 29.0, Status.HIGH), (0.0, 0.0, 0.0, Status.PASS)],
)
def test_e4_inclusive_limits(value: float, low: float, high: float, expected: Status) -> None:
    reading = Measurement("BUS", value, "V", low, high)
    assert classify(reading) is expected, f"for {reading} return enum member {expected}"


@pytest.mark.parametrize(
    "value,low,high,expected",
    [(-100.0, None, None, Status.PASS), (100.0, None, None, Status.PASS),
     (-1.0, 0.0, None, Status.LOW), (1.0, None, 0.0, Status.HIGH),
     (0.0, None, 0.0, Status.PASS), (0.0, 0.0, None, Status.PASS),
     (5.0, 0.0, None, Status.PASS), (-5.0, None, 0.0, Status.PASS)],
)
def test_e4_optional_limits(value: float, low: float | None, high: float | None, expected: Status) -> None:
    assert classify(Measurement("RETURN", value, "A", low, high)) is expected, "None removes only that bound"


def test_e4_does_not_convert_units() -> None:
    reading = Measurement("sense", 5.0, "mV", 4.0, 6.0)
    assert classify(reading) is Status.PASS, "value and limits already use the same unit"
    assert reading == Measurement("sense", 5.0, "mV", 4.0, 6.0), "keep the measurement unchanged"


def test_e5_summary_and_exact_json(measurement_csv: Path, tmp_path: Path) -> None:
    output = tmp_path / "operator reports" / "shift 1" / "summary.json"
    before = measurement_csv.read_bytes()
    got = write_summary(measurement_csv, output)
    expected = {"total": 4, "passed": 3, "failed": 1, "channels": 3}
    assert got == expected, "count rows and unique channel names separately"
    assert output.read_text(encoding="utf-8") == json.dumps(expected, indent=2, sort_keys=True) + "\n"
    assert measurement_csv.read_bytes() == before, "reporting must preserve the input CSV"


@pytest.mark.parametrize("body,expected", [
    ("", {"total": 0, "passed": 0, "failed": 0, "channels": 0}),
    ("BUS,-1,V,0,1\nBUS,2,V,0,1\nbus,0,V,,\n",
     {"total": 3, "passed": 1, "failed": 2, "channels": 2}),
])
def test_e5_counts_empty_and_repeated_channels(tmp_path: Path, body: str, expected: dict[str, int]) -> None:
    path = tmp_path / "in.csv"
    output = tmp_path / "out.json"
    path.write_text(HEADER + body, encoding="utf-8")
    assert write_summary(path, output) == expected, "count both LOW and HIGH as failed"
    assert json.loads(output.read_text(encoding="utf-8")) == expected


def test_e5_overwrite_previous_report(measurement_csv: Path, tmp_path: Path) -> None:
    output = tmp_path / "summary.json"
    output.write_text("old report" * 100, encoding="utf-8")
    expected = write_summary(measurement_csv, output)
    assert json.loads(output.read_text(encoding="utf-8")) == expected, "replace rather than append"


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("row,reason", [
    ("BUS,bad,V,0,1", "invalid number"),
    ('""', "expected 5 fields"),
    ('"   "', "expected 5 fields"),
])
def test_e5_invalid_input_preserves_output(tmp_path: Path, existing: bool, row: str, reason: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(HEADER + "BUS,0,V,0,1\n" + row + "\n", encoding="utf-8")
    output = tmp_path / "new reports" / "summary.json"
    if existing:
        output.parent.mkdir()
        output.write_bytes(b"previous report\r\n")
    with pytest.raises(RowError) as caught:
        write_summary(path, output)
    assert (caught.value.line_number, caught.value.reason) == (3, reason)
    if existing:
        assert output.read_bytes() == b"previous report\r\n", "keep the last report on bad input"
    else:
        assert not output.parent.exists(), "validate the whole input before creating output folders"


def test_e5_missing_input(tmp_path: Path) -> None:
    output = tmp_path / "new reports" / "summary.json"
    with pytest.raises(FileNotFoundError):
        write_summary(tmp_path / "missing.csv", output)
    assert not output.parent.exists(), "a missing input must not create output folders"
