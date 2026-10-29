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
import time
import xml.etree.ElementTree as ET

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


def cpp_compiler() -> tuple[str, bool, dict[str, str]]:
    """Prefer the installed Windows MSVC toolchain; otherwise use PATH."""
    env = os.environ.copy()
    if os.name == "nt":
        vswhere = Path(env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
        if vswhere.is_file():
            found = subprocess.run([str(vswhere), "-latest", "-products", "*", "-requires",
                                    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath", "-utf8"],
                                   capture_output=True, text=True, encoding="utf-8", timeout=30, check=True)
            if found.stdout.strip():
                vcvars = Path(found.stdout.strip()) / "VC/Auxiliary/Build/vcvars64.bat"
                command = f'"{env.get("COMSPEC", "cmd.exe")}" /d /u /s /c ""{vcvars}" >nul && set"'
                configured = subprocess.run(command, capture_output=True, text=True, encoding="utf-16-le", timeout=30)
                if configured.returncode:
                    raise ValueError("MSVC environment setup failed.\n" + configured.stdout + configured.stderr)
                for line in configured.stdout.splitlines():
                    key, separator, value = line.partition("=")
                    if separator and key and not key.startswith("="):
                        # Windows environment variable names are case insensitive.
                        key = key.upper()
                        env[key] = value
                compiler = shutil.which("cl.exe", path=env.get("PATH"))
                if not compiler:
                    raise ValueError("Visual Studio was found but cl.exe was not. Install Desktop development with C++.")
                return compiler, True, env
        candidates = ["g++"]
    else:
        candidates = [env["CXX"]] if env.get("CXX") else ["clang++", "g++"]
    for candidate in candidates:
        compiler = shutil.which(candidate)
        if compiler:
            return compiler, False, env
    raise ValueError("No C++ compiler found. Install Visual Studio C++ tools on Windows, or put g++/clang++ on PATH.")


def build_cpp(repo: Path, set_dir: Path, build: Path, toolchain: tuple[str, bool, dict[str, str]]) -> Path:
    compiler, msvc, env = toolchain
    build.mkdir(parents=True, exist_ok=True)
    includes = [set_dir / "include", repo / "third_party", repo / "third_party/doctest"]
    learner = sorted((set_dir / "starter").glob("*.cpp"))
    harness = sorted((set_dir / "tests").glob("*.cpp"))
    if not learner or not harness:
        raise ValueError("C++ sets need starter/*.cpp and tests/*.cpp.")
    if not any("DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN" in source.read_text(encoding="utf-8-sig") for source in harness):
        harness.append(repo / "third_party/doctest/doctest_main.cpp")
    common = (["/nologo", "/std:c++20", "/permissive-", "/EHsc", "/utf-8"] if msvc else ["-std=c++20"])
    for directory in includes:
        common += ["/I" + str(directory)] if msvc else ["-I", str(directory)]
    objects = []
    for index, source in enumerate(learner + harness):
        obj = build / f"{index}.{'obj' if msvc else 'o'}"
        warnings = ["/W4"] if msvc else ["-Wall", "-Wextra", "-Wpedantic"]
        if index < len(learner):
            warnings += ["/WX"] if msvc else ["-Werror", "-Wshadow", "-Wconversion", "-Wsign-conversion"]
        output = ["/c", str(source), "/Fo" + str(obj)] if msvc else ["-c", str(source), "-o", str(obj)]
        command = [compiler, *common, *warnings, *output]
        result = subprocess.run(command, cwd=build, env=env, capture_output=True, text=True, errors="replace", timeout=120)
        if result.returncode:
            raise ValueError("BUILD FAILED: fix the first compiler error below.\n" + result.stdout + result.stderr)
        objects.append(str(obj))
    executable = build / ("tests.exe" if os.name == "nt" else "tests")
    output = ["/Fe" + str(executable), "/link", "/INCREMENTAL:NO"] if msvc else ["-o", str(executable)]
    result = subprocess.run([compiler, *common, *objects, *output], cwd=build, env=env,
                            capture_output=True, text=True, errors="replace", timeout=120)
    if result.returncode:
        raise ValueError("BUILD FAILED at link time: check missing or duplicate definitions.\n" + result.stdout + result.stderr)
    return executable


def run_cpp_report(executable: Path) -> dict:
    def execute(*arguments: str) -> tuple[ET.Element, subprocess.CompletedProcess[str]]:
        result = subprocess.run([str(executable), "--reporters=xml", "--no-colors", *arguments],
                                cwd=executable.parent, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=10)
        try:
            return ET.fromstring(result.stdout), result
        except ET.ParseError as error:
            raise ValueError("The C++ tests stopped before producing a complete report (possible crash).\n"
                             + result.stdout + result.stderr) from error

    listing, listed = execute("--list-test-cases")
    expected = [case.get("name", "") for case in listing.findall(".//TestCase")]
    if listed.returncode or not expected or len(set(expected)) != len(expected):
        raise ValueError("C++ test discovery failed or test-case names are duplicated.")
    groups: dict[str, bool] = {}
    names = {}
    for name in expected:
        match = re.match(r"^E([1-9][0-9]*)(?:\s|$)", name)
        if not match:
            raise ValueError(f"C++ test-case names must start with E<number> and a space: {name!r}")
        key = f"E{int(match.group(1))}"
        names[name] = key
        groups[key] = True
    started = time.perf_counter()
    document, result = execute()
    elapsed = time.perf_counter() - started
    failures = []
    seen = set()
    for case in document.findall(".//TestCase"):
        name = case.get("name", "")
        if name not in names or name in seen:
            raise ValueError("Unexpected or duplicate C++ test-case result: " + name)
        seen.add(name)
        summary = case.find("OverallResultsAsserts")
        passed = summary is not None and summary.get("test_case_success") == "true" and case.get("skipped") != "true"
        groups[names[name]] &= passed
        if not passed:
            details = []
            for element in case.iter():
                if element.tag == "Expression" and element.get("success") == "false":
                    details.append(f"{element.get('filename')}:{element.get('line')}: "
                                   + " ".join(" ".join(element.itertext()).split()))
                elif element.tag in ("Exception", "Message"):
                    details.append(" ".join(" ".join(element.itertext()).split()))
            failures.append({"nodeid": name, "message": details[0][:300] if details else "Test skipped or incomplete."})
    errors = []
    if set(expected) != seen:
        errors.append("Some C++ test cases did not run.")
        for name in set(expected) - seen:
            groups[names[name]] = False
    summary = document.find("OverallResultsTestCases")
    if summary is None or summary.get("skipped", "0") != "0":
        errors.append("The C++ test run was incomplete or skipped tests.")
    output = []
    for key in sorted(groups, key=lambda value: int(value[1:])):
        failure = next((failure for failure in failures if names[failure["nodeid"]] == key), None)
        detail = f": {failure['nodeid']}: {failure['message']}" if failure else ""
        output.append(f"{'PASS' if groups[key] else 'FAIL'} {key}{detail}")
    passed = sum(groups.values())
    output += errors
    output.append(f"Exercises: {passed} / {len(groups)} passed")
    return {"passed": passed, "total": len(groups), "returncode": result.returncode,
            "errors": errors, "failures": failures, "output": "\n".join(output), "elapsed": elapsed}


def run_cpp_set(repo: Path, identifier: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="fasttrack-cpp-run-") as temporary:
        print(f"Building {identifier} ...", flush=True)
        executable = build_cpp(repo, repo / "sets" / identifier, Path(temporary), cpp_compiler())
        report = run_cpp_report(executable)
        print(report["output"])
        return all_pass(report)


def verify_cpp_set(repo: Path, solutions: Path, identifier: str, repeat: int, mypy: bool) -> bool:
    with tempfile.TemporaryDirectory(prefix="fasttrack-cpp-verify-") as temporary:
        work = Path(temporary)
        copied = work / "sets" / identifier
        shutil.copytree(repo / "sets" / identifier, copied, ignore=IGNORE)
        toolchain = cpp_compiler()
        executable = build_cpp(repo, copied, work / "build", toolchain)
        starter = run_cpp_report(executable)
        if not starter["total"] or starter["passed"] != 0 or starter["returncode"] != 1 or starter["errors"]:
            print(f"{identifier}: FAIL; starter: {score(starter)} (expected none)\n{starter['output']}")
            return False
        reference = solutions / "sets" / identifier / "starter"
        if not reference.is_dir() or not any(reference.glob("*.cpp")):
            raise ValueError(f"Reference C++ starter files are missing: {reference}")
        shutil.copytree(reference, copied / "starter", dirs_exist_ok=True, ignore=IGNORE)
        executable = build_cpp(repo, copied, work / "build", toolchain)
        for iteration in range(1, repeat + 1):
            result = run_cpp_report(executable)
            if not all_pass(result) or result["total"] != starter["total"]:
                print(f"{identifier}: FAIL; starter: {score(starter)}; reference run {iteration}: {score(result)}\n{result['output']}")
                return False
        suffix = ""
        if mypy:
            if any((copied / "starter").rglob("*.py")):
                checked = subprocess.run([sys.executable, "-m", "mypy", "--strict", str(copied / "starter")],
                                         cwd=copied, capture_output=True, text=True, encoding="utf-8", errors="replace")
                if checked.returncode:
                    print(f"{identifier}: FAIL; reference mypy\n{checked.stdout}{checked.stderr}")
                    return False
                suffix = "; mypy OK (Python scaffolding only; C++ compiler checks types)"
            else:
                suffix = "; mypy N/A (C++; compiler checks types)"
        print(f"{identifier}: OK; starter: {score(starter)}; reference: {score(result)} ({repeat} runs){suffix}")
        return True


def verify_set(repo: Path, solutions: Path, identifier: str, repeat: int, mypy: bool) -> bool:
    source = repo / "sets" / identifier
    if any((source / "tests").glob("*.cpp")):
        try:
            return verify_cpp_set(repo, solutions, identifier, repeat, mypy)
        except subprocess.SubprocessError as error:
            raise ValueError(f"C++ compiler or test command failed: {error}") from error
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
    parser.add_argument("--run-cpp", action="store_true", help="Build and run one C++ set (used by shell runners).")
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
    if args.run_cpp:
        if len(identifiers) != 1 or identifiers[0] not in choices or not any((ROOT / "sets" / identifiers[0] / "tests").glob("*.cpp")):
            parser.error("--run-cpp needs exactly one C++ set id.")
        try:
            return 0 if run_cpp_set(ROOT, identifiers[0]) else 1
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            print(f"{identifiers[0]}: FAIL; {error}")
            return 1
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
