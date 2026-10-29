"""Independent station review checks; no real hardware or system services."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zlib

import pytest

from starter.review5 import (
    Step, decode_ack, rerun_channels, review_reading, run_probe, run_sequence, parse_command,
)

SCRIPT = Path(__file__).resolve().parents[1] / "starter" / "station_summary.sh"
HISTORY = ["IDLE", "SETUP", "RUNNING"]


def test_e1_captures_both_streams_and_literal_arguments() -> None:
    code = "import sys; print(sys.argv[1]); print('probe diagnostic', file=sys.stderr)"
    literal = "station A; echo SHOULD_STAY_LITERAL"
    got = run_probe([sys.executable, "-c", code, literal], 2.0)
    assert got == (0, literal + "\n", "probe diagnostic\n"), f"preserve both streams and arguments: {got!r}"


@pytest.mark.parametrize("code", [1, 2, 17])
def test_e1_nonzero_exit_is_a_result(code: int) -> None:
    program = f"import sys; sys.stdout.write('partial '); sys.stderr.write('bad'); sys.exit({code})"
    got = run_probe([sys.executable, "-c", program], 2.0)
    assert got == (code, "partial ", "bad"), f"return exit {code} without stripping output: {got!r}"


def test_e1_timeout_discards_partial_output() -> None:
    # Bound the child even when the learner forgets to pass a timeout.
    program = "import sys, time\nprint('partial', flush=True)\nprint('error', file=sys.stderr, flush=True)\ntime.sleep(0.2)\n"
    got = run_probe([sys.executable, "-c", program], 0.1)
    assert got == (-9, "", "timeout"), f"use the documented timeout result: {got!r}"


def test_e1_launch_error_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_probe([str(tmp_path / "no-such-station-probe")], 1.0)


@pytest.fixture
def bash() -> str:
    executable = shutil.which("bash")
    if executable is None:
        pytest.skip("Bash is missing: install Git Bash or use Codespaces; E2 is unfinished.")
    return executable


def run_summary(bash: str, directory: Path, *args: str | Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    for key in ("BASH_ENV", "ENV", "SHELLOPTS", "BASHOPTS", "POSIXLY_CORRECT"):
        environment.pop(key, None)
    result = subprocess.run(
        [bash, "--noprofile", "--norc", SCRIPT.as_posix(),
         *(arg.as_posix() if isinstance(arg, Path) else arg for arg in args)],
        cwd=directory, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=3,
    )
    if result.returncode == 99 and result.stderr.startswith("NotImplementedError:"):
        raise NotImplementedError("E2: replace the unfinished body in starter/station_summary.sh")
    return result


@pytest.mark.parametrize(
    ("content", "expected", "code"),
    [(b"PASS\nFAIL\nPASS\nERROR\nFAIL\n", "PASS=2 FAIL=2 ERROR=1\n", 1),
     (b"PASS\nPASS\n", "PASS=2 FAIL=0 ERROR=0\n", 0),
     (b"ERROR\n", "PASS=0 FAIL=0 ERROR=1\n", 1),
     (b"", "PASS=0 FAIL=0 ERROR=0\n", 0)],
)
def test_e2_counts_outcomes(bash: str, tmp_path: Path, content: bytes, expected: str, code: int) -> None:
    source = tmp_path / "shift outcomes.txt"
    source.write_bytes(content)
    got = run_summary(bash, tmp_path, source)
    assert (got.returncode, got.stdout, got.stderr) == (code, expected, ""), f"bad summary: {got}"
    assert source.read_bytes() == content, "summarizing must preserve the source file"


def test_e2_crlf_last_line_and_literal_contents(bash: str, tmp_path: Path) -> None:
    source = tmp_path / "literal outcomes.txt"
    source.write_bytes(b"PASS\r\nFAIL\r\n PASS\nPASS \npass\n\n\\\n$(touch EXECUTED)\nERROR")
    got = run_summary(bash, tmp_path, source)
    assert (got.returncode, got.stdout, got.stderr) == (1, "PASS=1 FAIL=1 ERROR=1\n", ""), (
        f"match exact lines, handle CRLF and the unterminated last line: {got}"
    )
    assert not (tmp_path / "EXECUTED").exists(), "file content must never be executed"


@pytest.mark.parametrize("case", ["none", "extra", "missing", "directory"])
def test_e2_invalid_invocations(bash: str, tmp_path: Path, case: str) -> None:
    source = tmp_path / "outcomes.txt"
    source.write_text("PASS\n", encoding="utf-8")
    arguments: dict[str, list[str | Path]] = {
        "none": [], "extra": [source, "extra"], "missing": [tmp_path / "missing"], "directory": [tmp_path],
    }
    got = run_summary(bash, tmp_path, *arguments[case])
    assert (got.returncode, got.stdout, got.stderr) == (2, "", "Usage: bash station_summary.sh FILE\n"), (
        f"bad invocation must give only the usage diagnostic: {got}"
    )


def test_e2_strict_shell_options(bash: str, tmp_path: Path) -> None:
    source = tmp_path / "empty.txt"
    source.write_bytes(b"")
    got = run_summary(bash, tmp_path, source)
    assert got.returncode == 0, f"strict mode must still handle an empty file: {got}"
    assert re.search(r"^\s*set -euo pipefail\s*(?:#.*)?$", SCRIPT.read_text(encoding="utf-8"), re.MULTILINE), (
        "put set -euo pipefail on its own line before the summary work"
    )


@pytest.mark.parametrize("extra, expected", [([], False), (["--dry-run"], True)])
def test_e3_run_flag(extra: list[str], expected: bool) -> None:
    args = parse_command(["run", "--station", "bench-2", *extra])
    assert (args.command, args.station, args.dry_run) == ("run", "bench-2", expected)
    assert type(args.dry_run) is bool, "dry_run must be a Boolean"


def test_e3_show_order_and_input(capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["show", "--instrument", "PSU_1", "--station", " bench 2 "]
    original = argv.copy()
    args = parse_command(argv)
    assert (args.command, args.station, args.instrument) == ("show", " bench 2 ", "PSU_1")
    assert argv == original, "parsing must not change the caller's argument list"
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", ""), "successful parsing should be quiet"


@pytest.mark.parametrize("argv", [
    [], ["run"], ["show", "--station", "A"], ["reset"],
    ["run", "--station", "A", "--unknown"],
    ["run", "--station"], ["show", "--instrument", "psu"],
])
def test_e3_reject_bad_arguments(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        parse_command(argv)
    assert error.value.code == 2, "argument errors use argparse exit code 2"
    captured = capsys.readouterr()
    assert captured.err, "argparse should explain the error on stderr"
    assert captured.out == "", "argument errors should not print to stdout"


def station_step(
    name: str, events: list[str], *, outcome: bool = True,
    run_error: BaseException | None = None, cleanup_error: BaseException | None = None,
) -> Step:
    def run() -> bool:
        events.append(f"run:{name}")
        if run_error is not None:
            raise run_error
        return outcome

    def cleanup() -> None:
        events.append(f"cleanup:{name}")
        if cleanup_error is not None:
            raise cleanup_error

    return name, run, cleanup


def test_e4_success_and_reverse_cleanup() -> None:
    events: list[str] = []
    steps = [station_step("supply", events), station_step("scope", events)]
    original = list(steps)
    assert run_sequence(steps) == ("PASS", HISTORY + ["PASS"])
    assert events == ["run:supply", "run:scope", "cleanup:scope", "cleanup:supply"], "release in reverse order"
    assert steps == original, "leave the input sequence unchanged"


def test_e4_false_stops_and_cleans_failed_attempt() -> None:
    events: list[str] = []
    steps = [station_step("supply", events), station_step("scope", events, outcome=False), station_step("unused", events)]
    assert run_sequence(steps) == ("FAIL", HISTORY + ["FAIL"])
    assert events == ["run:supply", "run:scope", "cleanup:scope", "cleanup:supply"], "do not attempt or clean unused steps"


@pytest.mark.parametrize(("exception", "state"), [(RuntimeError("probe"), "ERROR"), (KeyboardInterrupt(), "ABORTED")])
def test_e4_run_exception_or_operator_abort(exception: BaseException, state: str) -> None:
    events: list[str] = []
    steps = [station_step("supply", events), station_step("scope", events, run_error=exception), station_step("unused", events)]
    assert run_sequence(steps) == (state, HISTORY + [state]), f"run exception should finish with {state}"
    assert events == ["run:supply", "run:scope", "cleanup:scope", "cleanup:supply"], "clean the raising run too"


@pytest.mark.parametrize("run_outcome", ["PASS", "FAIL", "ERROR", "ABORTED"])
@pytest.mark.parametrize("cleanup_error", [RuntimeError("release"), KeyboardInterrupt()])
def test_e4_cleanup_errors_override_and_continue(run_outcome: str, cleanup_error: BaseException) -> None:
    events: list[str] = []
    run_error = {"ERROR": RuntimeError("read"), "ABORTED": KeyboardInterrupt()}.get(run_outcome)
    steps = [station_step("supply", events, cleanup_error=ValueError("disconnect")),
             station_step("scope", events, outcome=run_outcome != "FAIL", run_error=run_error, cleanup_error=cleanup_error)]
    assert run_sequence(steps) == ("ERROR", HISTORY + ["ERROR"]), "cleanup failure takes precedence"
    assert events == ["run:supply", "run:scope", "cleanup:scope", "cleanup:supply"], "keep cleaning after a cleanup exception"


def test_e4_empty_sequence_and_fresh_history() -> None:
    state, history = run_sequence([])
    assert (state, history) == ("PASS", HISTORY + ["PASS"]), "empty review sequences pass"
    history.append("operator note")
    assert run_sequence([]) == ("PASS", HISTORY + ["PASS"]), "do not share history across runs"


def test_e4_other_base_exception_propagates_after_cleanup() -> None:
    events: list[str] = []
    with pytest.raises(SystemExit):
        run_sequence([station_step("supply", events, run_error=SystemExit(3))])
    assert events == ["run:supply", "cleanup:supply"], "even an uncaught exception must release attempted resources"


@pytest.mark.parametrize(
    ("value", "low", "high", "expected"),
    [(24.0, 24.0, 28.0, True), (28.0, 24.0, 28.0, True), (26.0, 24.0, 28.0, True),
     (24.0, 24.0, 24.0, True), (0.0, -0.0, 0.0, True), (-2.0, -3.0, -1.0, True),
     (23.0, 24.0, 28.0, False), (29.0, 24.0, 28.0, False)],
)
def test_e5_inclusive_limits(value: float, low: float, high: float, expected: bool) -> None:
    got = review_reading(value, low, high)
    assert got is expected, f"reading {value} within [{low}, {high}] should give {expected}, got {got!r}"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_e5_nonfinite_readings_fail(value: float) -> None:
    assert review_reading(value, 24.0, 28.0) is False, f"nonfinite reading {value} must fail"


@pytest.mark.parametrize(
    ("low", "high"),
    [(28.0, 24.0), (float("nan"), 28.0), (24.0, float("nan")),
     (float("-inf"), 28.0), (24.0, float("inf")), (float("inf"), 28.0), (24.0, float("-inf"))],
)
@pytest.mark.parametrize("value", [26.0, float("nan")])
def test_e5_invalid_limits_raise_first(value: float, low: float, high: float) -> None:
    with pytest.raises(ValueError):
        review_reading(value, low, high)


def test_e5_no_rounding() -> None:
    assert review_reading(23.999999999, 24.0, 28.0) is False, "do not round an out-of-range reading into the limits"
    assert review_reading(28.000000001, 24.0, 28.0) is False, "compare the original reading"


@pytest.mark.parametrize("as_string", [False, True])
def test_e6_reruns_follow_first_failure_order(tmp_path: Path, as_string: bool) -> None:
    source = tmp_path / "shift outcomes.csv"
    content = b"channel,status\r\nBUS_V,PASS\r\nTEMP_C,FAIL\r\nBUS_V,ERROR\r\nTEMP_C,PASS\r\nTEMP_C,ERROR\r\n"
    source.write_bytes(content)
    got = rerun_channels(str(source) if as_string else source)
    assert got == ["TEMP_C", "BUS_V"], f"order by first failing row, keeping each channel once: {got}"
    assert source.read_bytes() == content, "reading the rerun list must preserve the saved outcomes"


def test_e6_csv_quoting_blank_lines_and_exact_channel_text(tmp_path: Path) -> None:
    source = tmp_path / "outcomes.csv"
    source.write_text('channel,status\n\n"rack,2",ERROR\n BUS_V ,FAIL\nbus_v,FAIL\nBUS_V,FAIL\nTemp\u00e9,ERROR', encoding="utf-8")
    got = rerun_channels(source)
    assert got == ["rack,2", " BUS_V ", "bus_v", "BUS_V", "Temp\u00e9"], f"preserve CSV fields literally: {got}"


@pytest.mark.parametrize("rows", ["", "BUS_V,PASS\nTEMP_C,PASS\n", "\n\n"])
def test_e6_no_failures_returns_fresh_empty_list(tmp_path: Path, rows: str) -> None:
    source = tmp_path / "outcomes.csv"
    source.write_text("channel,status\n" + rows, encoding="utf-8")
    got = rerun_channels(source)
    assert got == [], f"no failing rows should give an empty list: {got}"
    got.append("operator note")
    assert rerun_channels(source) == [], "each call must build a new result"


@pytest.mark.parametrize("status", ["fail", " FAIL", "ERROR ", "", "UNKNOWN"])
def test_e6_invalid_status_raises(tmp_path: Path, status: str) -> None:
    source = tmp_path / "outcomes.csv"
    source.write_text(f"channel,status\nBUS_V,FAIL\nTEMP_C,{status}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        rerun_channels(source)
    source.write_text("channel,status\nTEMP_C,ERROR\n", encoding="utf-8")
    assert rerun_channels(source) == ["TEMP_C"], "invalid input must not leave a partial result for a later call"


def test_e6_missing_file_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        rerun_channels(tmp_path / "missing.csv")


def acknowledgment(sequence: int, status: int) -> bytes:
    body = sequence.to_bytes(2, "big") + bytes([status])
    return body + zlib.crc32(body).to_bytes(4, "big")


@pytest.mark.parametrize("sequence", [0, 1, 42, 256, 0x1234, 65535])
@pytest.mark.parametrize("status", [0, 1])
def test_e7_decodes_sequence_and_boolean(sequence: int, status: int) -> None:
    got = decode_ack(acknowledgment(sequence, status))
    assert got == (sequence, status == 1), f"decode big-endian sequence {sequence} and status {status}: {got}"
    assert got[1] is (status == 1), "acceptance must be a bool, not the numeric status byte"


@pytest.mark.parametrize("packet", [b"", b"\x00", b"\x00\x2a", b"\x00\x2a\x01", acknowledgment(42, 1)[:-1], acknowledgment(42, 1) + b"\x00"])
def test_e7_rejects_wrong_lengths(packet: bytes) -> None:
    with pytest.raises(ValueError):
        decode_ack(packet)


@pytest.mark.parametrize("status", [2, 127, 255])
def test_e7_rejects_unknown_status_even_with_valid_crc(status: int) -> None:
    with pytest.raises(ValueError):
        decode_ack(acknowledgment(42, status))


@pytest.mark.parametrize("offset", range(7))
def test_e7_rejects_corruption_in_each_byte(offset: int) -> None:
    damaged = bytearray(acknowledgment(42, 1))
    damaged[offset] ^= 1
    with pytest.raises(ValueError):
        decode_ack(bytes(damaged))


def test_e7_crc_covers_only_body_and_is_big_endian() -> None:
    packet = acknowledgment(42, 1)
    with pytest.raises(ValueError):
        decode_ack(packet[:3] + packet[3:][::-1])
    with pytest.raises(ValueError):
        decode_ack(packet[:3] + zlib.crc32(packet).to_bytes(4, "big"))
