from pathlib import Path
import sys

import pytest

from starter import opcli
from starter.opcli import build_parser, confirm, format_table, main


def test_e1_run_arguments() -> None:
    args = build_parser().parse_args([
        "run", "--limits", "rail limits.json", "--station", "bench-A", "--dry-run",
    ])
    assert (args.command, args.limits, args.station, args.dry_run) == (
        "run", "rail limits.json", "bench-A", True,
    ), "run must preserve option values and enable the dry-run flag"


def test_e1_defaults_and_other_commands() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--station", "bench-B", "--limits", "x.json"])
    assert args.dry_run is False, "measurement is the default when --dry-run is absent"
    assert parser.parse_args(["list"]).command == "list"
    shown = parser.parse_args(["show", "--station", "bench-offline"])
    assert (shown.command, shown.station) == ("show", "bench-offline")


@pytest.mark.parametrize("argv", [
    [], ["missing"], ["run"], ["run", "--station", "bench-A"],
    ["run", "--limits", "rail.json"], ["show"],
    ["show", "--station", "unknown"], ["list", "extra"],
    ["run", "--limits", "x", "--station", "unknown"],
    ["run", "--limits", "x", "--station", "bench-A", "--bogus"],
    ["run", "--limits", "x", "--station", "bench-A", "--dry-run", "yes"],
])
def test_e1_usage_errors_raise_without_printing(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ValueError):
        build_parser().parse_args(argv)
    captured = capsys.readouterr()
    assert captured.out == captured.err == "", "E1 must leave error formatting to main"


@pytest.mark.parametrize(("argv", "words"), [
    (["--help"], ["run", "list", "show"]),
    (["run", "--help"], ["--limits", "--station", "--dry-run"]),
    (["list", "-h"], ["list"]), (["show", "-h"], ["--station"]),
])
def test_e1_help(argv: list[str], words: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stopped:
        build_parser().parse_args(argv)
    assert stopped.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("usage: station"), "help must identify the operator tool"
    assert all(word in captured.out for word in words), "help must expose the command options"
    assert captured.err == ""


@pytest.mark.parametrize(("station", "bounds", "dry_run", "expected_code", "expected_out", "expected_err"), [
    ("bench-A", (4.5, 5.5), False, 0, "bench-A: PASS\n", ""),
    ("bench-A", (5.0, 5.0), False, 0, "bench-A: PASS\n", ""),
    ("bench-A", (0.0, 10**400), False, 0, "bench-A: PASS\n", ""),
    ("bench-B", (4.5, 5.5), False, 1, "bench-B: FAIL\n", ""),
    ("bench-A", (1.0, 4.0), False, 1, "bench-A: FAIL\n", ""),
    ("bench-offline", (4.5, 5.5), False, 2, "", "error: bench-offline: measurement unavailable\n"),
    ("bench-B", (4.5, 5.5), True, 0, "bench-B: READY\n", ""),
    ("bench-offline", (4.5, 5.5), True, 0, "bench-offline: READY\n", ""),
])
def test_e2_run_outcomes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], station: str,
    bounds: tuple[float, float], dry_run: bool, expected_code: int,
    expected_out: str, expected_err: str,
) -> None:
    limits = tmp_path / "rail limits.json"
    limits.write_text(f'{{"low": {bounds[0]}, "high": {bounds[1]}}}', encoding="utf-8")
    argv = ["run", "--limits", str(limits), "--station", station]
    if dry_run:
        argv.append("--dry-run")
    result = main(argv)
    captured = capsys.readouterr()
    assert type(result) is int and result == expected_code, "return the documented integer exit code"
    assert captured.out == expected_out
    assert captured.err == expected_err


@pytest.mark.parametrize(("argv", "output"), [
    (["list"], "bench-A\nbench-B\nbench-offline\n"),
    (["show", "--station", "bench-A"], "bench-A: 5.0 V\n"),
    (["show", "--station", "bench-B"], "bench-B: 4.0 V\n"),
    (["show", "--station", "bench-offline"], "bench-offline: offline\n"),
])
def test_e2_list_and_show(argv: list[str], output: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.out == output
    assert captured.err == ""


@pytest.mark.parametrize(("argv", "clue"), [
    ([], "command"), (["unknown"], "unknown"),
    (["run", "--station", "bench-A"], "--limits"),
    (["run", "--limits", "x"], "--station"),
    (["show", "--station", "unknown"], "unknown"),
    (["list", "--bogus"], "--bogus"),
])
def test_e2_usage_errors(argv: list[str], clue: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 3, "usage mistakes use code 3, not argparse's default code 2"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: ") and len(captured.err.splitlines()) == 1
    assert clue in captured.err, "keep the diagnostic that helps the operator fix the command"
    assert "Traceback" not in captured.err and "usage:" not in captured.err


@pytest.mark.parametrize("content", [
    None, "not JSON", '{"low": 8, "high": 2}', '{"low": true, "high": 6}',
    '{"low": 0}', '{"low": "4", "high": 6}', '{"low": 0, "high": Infinity}',
    b"\xff",
])
def test_e2_input_errors_even_in_dry_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str | bytes | None,
) -> None:
    limits = tmp_path / "bad limits.json"
    if isinstance(content, bytes):
        limits.write_bytes(content)
    elif content is not None:
        limits.write_text(content, encoding="utf-8")
    assert main(["run", "--limits", str(limits), "--station", "bench-A", "--dry-run"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: ") and len(captured.err.splitlines()) == 1
    assert "Traceback" not in captured.err
    if content is None:
        assert limits.name in captured.err, "a missing-file message must retain its filename"


@pytest.mark.parametrize("argv", [["--help"], ["run", "--help"], ["list", "-h"], ["show", "-h"]])
def test_e2_help_and_real_argv(
    argv: list[str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(argv) == 0, "main must return rather than leak help's SystemExit"
    captured = capsys.readouterr()
    assert captured.out.startswith("usage: station") and captured.err == ""
    monkeypatch.setattr(sys, "argv", ["station", "list"])
    assert main(None) == 0
    captured = capsys.readouterr()
    assert captured.out == "bench-A\nbench-B\nbench-offline\n" and captured.err == ""


def test_e2_dispatch_and_multiline_diagnostic(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, str, bool]] = []

    def backend(path: str, station: str, dry_run: bool) -> str:
        calls.append((path, station, dry_run))
        raise ValueError("  limits rail.json:\n  expected numeric bounds\t ")

    monkeypatch.setattr(opcli, "_run_station", backend)
    assert main(["run", "--limits", "rail.json", "--station", "bench-A", "--dry-run"]) == 3
    assert calls == [("rail.json", "bench-A", True)], "dispatch exactly once with parsed arguments"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: limits rail.json: expected numeric bounds\n"


def test_e3_align_and_preserve_inputs(capsys: pytest.CaptureFixture[str]) -> None:
    rows: list[dict[str, object]] = [
        {"station": "A", "state": "PASS"}, {"station": "long-bench", "state": "FAIL"},
    ]
    original = [row.copy() for row in rows]
    columns = ["station", "state"]
    result = format_table(rows, columns)
    assert result == "station     state\nA           PASS\nlong-bench  FAIL"
    assert rows == original and columns == ["station", "state"], "formatting must not change source data"
    assert capsys.readouterr().out == "", "return the table rather than printing it"


def test_e3_requested_order_and_conversions() -> None:
    rows: list[dict[str, object]] = [
        {"station": "A", "value": 5.25, "ignored": "do-not-display"},
        {"station": "B", "value": None}, {"station": "C", "value": False},
    ]
    assert format_table(rows, ["value", "station"]) == (
        "value  station\n5.25   A\nNone   B\nFalse  C"
    ), "column order comes from columns, and values use str()"


def test_e3_missing_cells_and_no_trailing_spaces() -> None:
    rows: list[dict[str, object]] = [{"state": "PASS"}, {"station": "A"}, {}]
    assert format_table(rows, ["station", "state"]) == "station  state\n         PASS\nA\n"
    assert format_table([{"volts": 5}], ["volts"]) == "volts\n5"


@pytest.mark.parametrize(("rows", "columns", "expected"), [
    ([], ["station", "state"], "station  state"),
    ([], [], ""), ([{"station": "A"}], [], ""),
])
def test_e3_empty_inputs(rows: list[dict[str, object]], columns: list[str], expected: str) -> None:
    assert format_table(rows, columns) == expected


@pytest.mark.parametrize("reply", ["y", "yes", "Y", "YES", "  YeS ", "\ty\n"])
def test_e4_explicit_yes(reply: str) -> None:
    assert confirm("Enable output?", lambda prompt: reply) is True


@pytest.mark.parametrize("reply", ["", " ", "n", "NO", "sure", "yes please", "yep", "1", "y es"])
def test_e4_every_other_reply_is_no(reply: str) -> None:
    assert confirm("Enable output?", lambda prompt: reply) is False


def test_e4_prompt_once_and_no_extra_output(capsys: pytest.CaptureFixture[str]) -> None:
    prompts: list[str] = []

    def input_fn(prompt: str) -> str:
        prompts.append(prompt)
        return "no"

    assert confirm("Enable PSU output?", input_fn) is False
    assert prompts == ["Enable PSU output? [y/N] "], "show the safe default and ask only once"
    captured = capsys.readouterr()
    assert captured.out == captured.err == "", "the input function owns displaying the prompt"


def test_e4_closed_input_is_safe() -> None:
    prompts: list[str] = []

    def closed_input(prompt: str) -> str:
        prompts.append(prompt)
        raise EOFError

    assert confirm("Enable output?", closed_input) is False, "closed input must never enable output"
    assert prompts == ["Enable output? [y/N] "]
