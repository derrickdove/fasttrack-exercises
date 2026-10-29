"""Verify isolated starters and references without changing either repository."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".mypy_cache", ".venv", ".git")


def available(repo: Path) -> list[str]:
    sets = sorted(path.name for path in (repo / "sets").iterdir() if path.is_dir())
    gates = sorted(path.name for path in (repo / "gates").glob("b[1-6]") if path.is_dir())
    return sets + gates


def run_report(repo: Path, targets: list[Path], work: Path, *, capstone: Path | None = None) -> dict:
    report = work / "report.json"
    report.unlink(missing_ok=True)
    env = os.environ.copy()
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="", PYTHONDONTWRITEBYTECODE="1")
    env["PYTHONPATH"] = str(repo)
    env.pop("FT_REPORT_MODE", None)
    if capstone is not None:
        env.update(FT_CAPSTONE=str(capstone), FT_REPORT_MODE="checks")
    command = [sys.executable, "-m", "pytest", *map(str, targets), "-p", "tools.ft_report",
               "-q", "--no-header", "--rootdir", str(repo), "--ft-report-json", str(report)]
    result = subprocess.run(command, cwd=repo, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not report.exists():
        raise ValueError("The test report was not produced.\n" + result.stdout + result.stderr)
    data = json.loads(report.read_text(encoding="utf-8"))
    data["returncode"] = result.returncode
    data["output"] = result.stdout + result.stderr
    return data


def all_pass(report: dict) -> bool:
    return bool(report["total"]) and report["passed"] == report["total"] and report["returncode"] == 0 and not report["errors"]


def score(report: dict) -> str:
    return f"{report['passed']} / {report['total'] if report['total'] is not None else '?'}"


def verify_cpp_set(set_dir: Path) -> bool:
    """d41 extension hook: replace the skip with C++ starter/reference verification."""
    print(f"{set_dir.name}: C++ set: skipped (handled by the d41 job)")
    return True


def verify_set(repo: Path, solutions: Path, identifier: str, repeat: int, mypy: bool) -> bool:
    source = repo / "sets" / identifier
    if any((source / "tests").glob("*.cpp")):
        return verify_cpp_set(source)
    with tempfile.TemporaryDirectory(prefix="fasttrack-verify-") as temporary:
        work = Path(temporary)
        copied = work / "sets" / identifier
        shutil.copytree(source, copied, ignore=IGNORE)
        metadata_file = copied / ".verify.json"
        metadata = json.loads(metadata_file.read_text(encoding="utf-8")) if metadata_file.exists() else {}
        if not isinstance(metadata, dict) or set(metadata) - {"starter_expect"}:
            raise ValueError(".verify.json supports only starter_expect: 'none' or 'all'.")
        expectation = metadata.get("starter_expect", "none")
        if expectation not in ("none", "all"):
            raise ValueError(".verify.json starter_expect must be 'none' or 'all'.")
        starter = run_report(repo, [copied], work)
        if expectation == "all":
            starter_ok = all_pass(starter)
        else:
            starter_ok = (bool(starter["total"]) and starter["passed"] == 0
                          and starter["returncode"] == 1 and not starter["errors"]
                          and bool(starter["failures"])
                          and all(failure["not_implemented"] for failure in starter["failures"]))
        if not starter_ok:
            print(f"{identifier}: FAIL; starter: {score(starter)} (expected {expectation})\n{starter['output']}")
            return False
        reference = solutions / "sets" / identifier / "starter"
        if not reference.is_dir() or not any(reference.rglob("*.py")):
            raise ValueError(f"Reference starter files are missing: {reference}")
        shutil.copytree(reference, copied / "starter", dirs_exist_ok=True, ignore=IGNORE)
        for iteration in range(1, repeat + 1):
            result = run_report(repo, [copied], work)
            if not all_pass(result) or result["total"] != starter["total"]:
                print(f"{identifier}: FAIL; starter: {score(starter)}; reference run {iteration}: {score(result)}\n{result['output']}")
                return False
        if mypy:
            command = [sys.executable, "-m", "mypy", "--strict"]
            config = copied / "mypy.ini"
            if config.exists():
                command += ["--config-file", str(config)]
            command += [str(copied / "starter")]
            checked = subprocess.run(command, cwd=copied, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if checked.returncode:
                print(f"{identifier}: FAIL; reference mypy\n{checked.stdout}{checked.stderr}")
                return False
        suffix = "; mypy OK" if mypy else ""
        print(f"{identifier}: OK; starter: {score(starter)}; reference: {score(result)} ({repeat} runs){suffix}")
        return True


def verify_gate(repo: Path, solutions: Path, identifier: str, repeat: int, mypy: bool) -> bool:
    targets = [repo / "gates" / f"b{number}" for number in range(1, int(identifier[1:]) + 1)]
    if any(not path.is_dir() for path in targets):
        raise ValueError("An earlier gate folder is missing; cumulative verification needs b1 through " + identifier + ".")
    with tempfile.TemporaryDirectory(prefix="fasttrack-gate-") as temporary:
        work = Path(temporary)
        capstone = work / "capstone"
        shutil.copytree(repo / "capstone", capstone, ignore=IGNORE)
        starter = run_report(repo, targets, work, capstone=capstone)
        if starter["passed"] != 0:
            print(f"{identifier}: FAIL; bare capstone: {score(starter)} (expected 0 passed)\n{starter['output']}")
            return False
        reference = solutions / "capstone"
        if not reference.is_dir() or not any(reference.rglob("*.py")):
            raise ValueError(f"Reference capstone files are missing: {reference}")
        shutil.copytree(reference, capstone, dirs_exist_ok=True, ignore=IGNORE)
        for iteration in range(1, repeat + 1):
            result = run_report(repo, targets, work, capstone=capstone)
            if not all_pass(result):
                print(f"{identifier}: FAIL; bare capstone: {score(starter)}; reference run {iteration}: {score(result)}\n{result['output']}")
                return False
        if mypy:
            checked = subprocess.run([sys.executable, "-m", "mypy", "--strict", "chassis"], cwd=capstone,
                                     capture_output=True, text=True, encoding="utf-8", errors="replace")
            if checked.returncode:
                print(f"{identifier}: FAIL; reference mypy\n{checked.stdout}{checked.stderr}")
                return False
        suffix = "; mypy OK" if mypy else ""
        print(f"{identifier}: OK; bare capstone: {score(starter)}; reference: {score(result)} ({repeat} runs){suffix}")
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--all", action="store_true", help="Verify every existing set and gate.")
    parser.add_argument("--repeat", type=int, default=1, help="Number of reference runs (at least 1).")
    parser.add_argument("--mypy", action="store_true", help="Also check reference types with mypy --strict.")
    parser.add_argument("--solutions", type=Path, default=ROOT.parent / "fasttrack-exercises-solutions")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    choices = available(ROOT)
    identifiers = list(dict.fromkeys(args.ids + (choices if args.all else [])))
    if not identifiers:
        parser.error("Choose a set or gate, or use --all. Available: " + ", ".join(choices))
    good = True
    for identifier in identifiers:
        try:
            if identifier not in choices:
                raise ValueError("Unknown id. Available: " + ", ".join(choices))
            function = verify_gate if re.fullmatch(r"b[1-6]", identifier) else verify_set
            good = function(ROOT, args.solutions.resolve(), identifier, args.repeat, args.mypy) and good
        except (OSError, ValueError, shutil.Error) as error:
            print(f"{identifier}: FAIL; {error}")
            good = False
    return 0 if good else 1


if __name__ == "__main__":
    raise SystemExit(main())
