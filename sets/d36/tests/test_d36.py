"""Execute the learner's Bash files against isolated station directories."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from starter.scripts import SCRIPT_DIR

COLLECT_USAGE = "Usage: bash collect_logs.sh SRC DEST\n"
CHECK_USAGE = "Usage: bash check_station.sh [--json] CONFIG\n"
COMPLETE = "station_id=bench-7\ninstrument_host=192.0.2.8\nlog_dir=/var/log/station\n"


@pytest.fixture
def bash() -> str:
    executable = shutil.which("bash")
    if executable is None:
        pytest.skip("Bash is missing: install Git Bash on Windows or use Codespaces; d36 is unfinished.")
    return executable


def run_script(
    bash: str,
    tmp_path: Path,
    name: str,
    *arguments: str | Path,
    exercise: int,
    hooks: str = "",
) -> subprocess.CompletedProcess[str]:
    # BASH_ENV supplies test commands without requiring executable file permissions.
    # Forward slashes work in Git Bash and native Linux Bash alike.
    environment = os.environ.copy()
    for key in ("BASH_ENV", "ENV", "SHELLOPTS", "BASHOPTS", "POSIXLY_CORRECT"):
        environment.pop(key, None)
    hook_file = tmp_path / "bash-test-env.sh"
    hook_file.write_text("date() { printf '20310405\\n'; }\n" + hooks, encoding="utf-8")
    environment["BASH_ENV"] = hook_file.as_posix()
    result = subprocess.run(
        [bash, "--noprofile", "--norc", (SCRIPT_DIR / name).as_posix(),
         *(arg.as_posix() if isinstance(arg, Path) else arg for arg in arguments)],
        cwd=tmp_path, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=3,
    )
    if result.returncode == 99 and result.stderr.startswith("NotImplementedError:"):
        raise NotImplementedError(f"E{exercise}: replace the unfinished body in starter/{name}")
    return result


def config_file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "station settings.conf"
    path.write_bytes(text.encode("utf-8"))
    return path


def test_e1_collects_only_top_level_logs_and_preserves_sources(bash: str, tmp_path: Path) -> None:
    src = tmp_path / "bench logs"
    src.mkdir()
    (src / "power check.log").write_bytes(b"CH1=24.0\n")
    (src / "-scope.log").write_bytes(b"\x00\xffcapture")
    os.utime(src / "power check.log", (946684800, 946684800))
    (src / "notes.txt").write_text("operator note", encoding="utf-8")
    (src / "UPPER.LOG").write_text("ignore", encoding="utf-8")
    (src / ".private.log").write_text("ignore", encoding="utf-8")
    nested = src / "old.log"
    nested.mkdir()
    (nested / "nested.log").write_text("ignore", encoding="utf-8")
    dest = tmp_path / "new archive" / "shift"
    result = run_script(bash, tmp_path, "collect_logs.sh", src, dest, exercise=1)
    assert result.returncode == 0, f"collection failed: {result.stderr}"
    assert result.stdout == result.stderr == "", "successful collection must be quiet"
    target = dest / "20310405"
    assert sorted(p.name for p in target.iterdir()) == ["-scope.log", "power check.log"]
    for name in ("power check.log", "-scope.log"):
        assert (target / name).read_bytes() == (src / name).read_bytes(), f"copy corrupted {name}"


def test_e1_empty_source_and_existing_archive(bash: str, tmp_path: Path) -> None:
    src = tmp_path / "empty"
    src.mkdir()
    dest = tmp_path / "archive"
    result = run_script(bash, tmp_path, "collect_logs.sh", src, dest, exercise=1)
    assert result.returncode == 0, f"an empty source is valid: {result.stderr}"
    target = dest / "20310405"
    assert target.is_dir() and not list(target.iterdir()), "create the dated folder even without logs"
    (src / "relay.log").write_text("new", encoding="utf-8")
    (target / "relay.log").write_text("old", encoding="utf-8")
    (target / "other.log").write_text("keep", encoding="utf-8")
    result = run_script(bash, tmp_path, "collect_logs.sh", src, dest, exercise=1)
    assert result.returncode == 0, result.stderr
    assert (target / "relay.log").read_text(encoding="utf-8") == "new", "replace an older copy"
    assert (target / "other.log").read_text(encoding="utf-8") == "keep", "keep unrelated archive files"


@pytest.mark.parametrize("case", ["none", "one", "extra", "missing", "file"])
def test_e1_bad_arguments(bash: str, tmp_path: Path, case: str) -> None:
    src = tmp_path / "src"
    src.mkdir()
    regular = tmp_path / "not a directory"
    regular.write_text("config", encoding="utf-8")
    dest = tmp_path / "must not exist"
    args = {
        "none": [], "one": [src], "extra": [src, dest, "extra"],
        "missing": [tmp_path / "missing", dest], "file": [regular, dest],
    }[case]
    result = run_script(bash, tmp_path, "collect_logs.sh", *args, exercise=1)
    assert result.returncode == 2, f"bad arguments need exit 2: {result}"
    assert result.stdout == "" and result.stderr == COLLECT_USAGE
    assert not dest.exists(), "validate arguments before creating destination folders"


def test_e2_enables_strict_options(bash: str, tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    result = run_script(bash, tmp_path, "collect_logs.sh", src, tmp_path / "archive", exercise=2)
    assert result.returncode == 0, result.stderr
    text = (SCRIPT_DIR / "collect_logs.sh").read_text(encoding="utf-8")
    assert re.search(r"^\s*set -euo pipefail\s*(?:#.*)?$", text, re.MULTILINE), (
        "put set -euo pipefail on its own line before the collection work"
    )


@pytest.mark.parametrize("command", ["cp", "mkdir", "date"])
def test_e2_stops_on_failed_command(bash: str, tmp_path: Path, command: str) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for name in ("a.log", "b.log"):
        (src / name).write_text(name, encoding="utf-8")
    hooks = f"{command}() {{ printf '%s\\n' {command} >> attempts.txt; return 37; }}\n"
    result = run_script(
        bash, tmp_path, "collect_logs.sh", src, tmp_path / "archive", exercise=2, hooks=hooks,
    )
    assert result.returncode != 0, f"a failed {command} must stop the collection"
    attempts = (tmp_path / "attempts.txt").read_text(encoding="utf-8").splitlines()
    assert attempts == [command], f"stop after the first {command} failure, got {attempts}"
    assert not list((tmp_path / "archive").rglob("*.log")), "do not copy after a prerequisite fails"


def test_e3_complete_config_with_literal_values(bash: str, tmp_path: Path) -> None:
    config = config_file(
        tmp_path,
        "# station settings\r\n\r\nstation_id=$(touch INJECTION)\r\n"
        "instrument_host=scope=primary\r\nunknown=ignored\r\nlog_dir=C:\\station logs",
    )
    result = run_script(bash, tmp_path, "check_station.sh", config, exercise=3)
    assert result.returncode == 0, f"all required values are present: {result.stderr}"
    assert result.stdout == "Station OK\n" and result.stderr == ""
    assert not (tmp_path / "INJECTION").exists(), "read configuration as data, never execute it"


def test_e3_missing_and_empty_keys_in_required_order(bash: str, tmp_path: Path) -> None:
    config = config_file(tmp_path, "# station_id=comment\nlog_dir=\ninstrument_host=\n")
    result = run_script(bash, tmp_path, "check_station.sh", config, exercise=3)
    assert result.returncode == 1, "missing settings require exit 1"
    assert result.stdout == "Missing: station_id\nMissing: instrument_host\nMissing: log_dir\n"
    assert result.stderr == ""



def test_e3_whitespace_and_backslash_are_literal_values(bash: str, tmp_path: Path) -> None:
    config = config_file(tmp_path, "station_id= \ninstrument_host=scope\nlog_dir=\\")
    result = run_script(bash, tmp_path, "check_station.sh", config, exercise=3)
    assert result.returncode == 0, "a space and a literal backslash are nonempty values"
    assert result.stdout == "Station OK\n" and result.stderr == ""


def test_e3_last_value_wins(bash: str, tmp_path: Path) -> None:
    config = config_file(tmp_path, COMPLETE + "station_id=\ninstrument_host=backup\n")
    result = run_script(bash, tmp_path, "check_station.sh", config, exercise=3)
    assert result.returncode == 1, "a later empty value clears an earlier setting"
    assert result.stdout == "Missing: station_id\n" and result.stderr == ""


@pytest.mark.parametrize("case", ["none", "extra", "missing", "directory", "option"])
def test_e3_usage_errors(bash: str, tmp_path: Path, case: str) -> None:
    config = config_file(tmp_path, COMPLETE)
    args = {"none": [], "extra": [config, config], "missing": [tmp_path / "absent"],
            "directory": [tmp_path], "option": ["--unknown"]}[case]
    result = run_script(bash, tmp_path, "check_station.sh", *args, exercise=3)
    assert result.returncode == 2, f"invalid invocation must return 2: {result}"
    assert result.stdout == "" and result.stderr == CHECK_USAGE


@pytest.mark.parametrize(
    ("text", "missing"),
    [(COMPLETE, []), ("station_id=bench-7\n", ["instrument_host", "log_dir"]),
     ("", ["station_id", "instrument_host", "log_dir"]),
     (COMPLETE + "log_dir=\r\n", ["log_dir"])],
)
def test_e4_json_matches_config_result(bash: str, tmp_path: Path, text: str, missing: list[str]) -> None:
    config = config_file(tmp_path, text)
    result = run_script(bash, tmp_path, "check_station.sh", "--json", config, exercise=4)
    assert result.returncode == (1 if missing else 0), "JSON mode keeps the text mode exit status"
    assert result.stderr == "", f"valid JSON invocation wrote diagnostics: {result.stderr}"
    assert result.stdout.endswith("\n") and len(result.stdout.splitlines()) == 1, "emit one JSON line"
    payload = json.loads(result.stdout)
    assert payload == {"ok": not missing, "missing": missing}, f"wrong station report: {payload}"
    assert type(payload["ok"]) is bool, "ok must be a JSON Boolean"


@pytest.mark.parametrize("extra", [[], ["config", "extra"], ["absent"]])
def test_e4_json_usage_errors(bash: str, tmp_path: Path, extra: list[str]) -> None:
    result = run_script(bash, tmp_path, "check_station.sh", "--json", *extra, exercise=4)
    assert result.returncode == 2, "--json still requires exactly one config path"
    assert result.stdout == "" and result.stderr == CHECK_USAGE
