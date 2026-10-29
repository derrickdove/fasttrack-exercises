"""Small learner report; --ft-report-json also gives verify_sets exact outcomes."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

import pytest

EXERCISE = re.compile(r"^test_e(\d+)_")
TEST_NAME = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)\s*\(", re.MULTILINE)


def pytest_addoption(parser):
    parser.addoption("--ft-report-json", metavar="PATH", help="Write the verification report as JSON.")


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    # Use pytest's collection/execution machinery, with only our learner-facing output.
    terminal = config.pluginmanager.getplugin("terminalreporter")
    if terminal is not None:
        config.pluginmanager.unregister(terminal)
    config._ft_report = {"items": {}, "results": {}, "errors": [], "failures": []}


def pytest_collection_finish(session):
    state = session.config._ft_report
    for item in session.items:
        name = getattr(item, "originalname", None) or item.name.split("[")[0]
        state["items"][item.nodeid] = {"name": name, "path": str(item.path)}


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    state = item.config._ft_report
    successful = report.passed and not getattr(report, "wasxfail", False)
    previous = state["results"].get(report.nodeid, True)
    state["results"][report.nodeid] = previous and successful
    if not successful:
        crash = getattr(report.longrepr, "reprcrash", None)
        message = crash.message if crash else str(report.longrepr or "Expected failure did not pass")
        message = " ".join(message.splitlines())[:300]
        error_type = call.excinfo.type if call.excinfo else None
        state["failures"].append({
            "nodeid": report.nodeid, "phase": report.when, "message": message,
            "exception": error_type.__name__ if error_type else report.outcome,
            "not_implemented": bool(error_type and issubclass(error_type, NotImplementedError)),
        })
    return report


@pytest.hookimpl(wrapper=True)
def pytest_make_collect_report(collector):
    report = yield
    if report.failed:
        collector.config._ft_report["errors"].append(str(report.longrepr))
    return report


def _source_tests(config):
    """Recover names from source when a learner import prevents collection."""
    found = {}
    for argument in config.args:
        path = Path(str(argument).split("::")[0])
        paths = [path] if path.is_file() else sorted(path.rglob("test_*.py"))
        for source in paths:
            if source.suffix != ".py":
                continue
            try:
                names = TEST_NAME.findall(source.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError):
                continue
            for name in names:
                found[f"{source.resolve()}::{name}"] = {"name": name, "path": str(source.resolve())}
    return found


def pytest_sessionfinish(session, exitstatus):
    # End global capture before writing: no terminal reporter remains to do it.
    capture = session.config.pluginmanager.getplugin('capturemanager')
    if capture is not None:
        capture.stop_global_capturing()
    state = session.config._ft_report
    items = dict(state["items"])
    if state["errors"]:
        known = {(str(Path(item["path"]).resolve()), item["name"]) for item in items.values()}
        for key, item in _source_tests(session.config).items():
            if (item["path"], item["name"]) not in known:
                items[key] = item
    checks = os.environ.get("FT_REPORT_MODE") == "checks" or any(
        "gates" in Path(item["path"]).parts or not EXERCISE.match(item["name"])
        for item in items.values()
    )
    groups = {}
    for nodeid, item in items.items():
        match = EXERCISE.match(item["name"])
        key = nodeid if checks else f"E{int(match.group(1))}"
        group = groups.setdefault(key, {"passed": True, "message": "", "nodes": []})
        group["nodes"].append(nodeid)
        group["passed"] &= state["results"].get(nodeid, False) and not state["errors"]
        failure = next((entry for entry in state["failures"] if entry["nodeid"] == nodeid), None)
        if failure and not group["message"]:
            group["message"] = failure["message"]
    passed = sum(group["passed"] for group in groups.values())
    total = len(groups) or None
    kind = "Checks" if checks else "Exercises"
    for error in state["errors"]:
        print(f"Your code could not be loaded:\n{error}", flush=True)
    ordered = sorted(groups) if checks else sorted(groups, key=lambda key: int(key[1:]))
    for key in ordered:
        group = groups[key]
        label = key if not checks else key.split("::", 1)[-1]
        message = f": {group['message']}" if group["message"] else ""
        print(f"{'PASS' if group['passed'] else 'FAIL'} {label}{message}", flush=True)
    if exitstatus and not state["errors"] and not state["failures"]:
        print("The tests stopped before finishing. Check the test files and run again.", flush=True)
    if not total or passed != total or state["errors"]:
        session.exitstatus = 1
    destination = session.config.getoption("--ft-report-json")
    if destination:
        Path(destination).write_text(json.dumps({
            "kind": kind, "passed": passed, "total": total,
            "errors": state["errors"], "failures": state["failures"],
            "exitstatus": int(session.exitstatus),
        }, indent=2), encoding="utf-8")
    print(f"{kind}: {passed} / {total if total is not None else '?'} passed", flush=True)
