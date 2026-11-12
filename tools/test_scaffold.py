"""Shared-tool regression checks; all fixtures live in deleted temporary folders."""
from contextlib import redirect_stdout
from datetime import datetime
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from gen_tasks import set_order
from ft_times import report as timing_report
from verify_sets import run_report

ROOT = Path(__file__).resolve().parents[1]


class TaskChecks(unittest.TestCase):
    def test_plan_order(self):
        names = ["check54", "d53", "d51", "r6", "d48", "d36", "r4", "check34", "d33", "d15", "r1", "d13", "d00-hello"]
        self.assertEqual(sorted(names, key=set_order), list(reversed(names)))


class TimingChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fasttrack timing ")
        self.addCleanup(self.temporary.cleanup)
        self.log = Path(self.temporary.name) / "progress.jsonl"

    def write_run(self, time, passed=(), failed=("E1", "E2", "E3"), identifier="probe"):
        with self.log.open("a", encoding="utf-8") as log:
            log.write(json.dumps({"time": time, "set": identifier, "passed": list(passed),
                                  "failed": list(failed), "total": len(passed) + len(failed)}) + "\n")

    def test_minutes_first_pass_survives_regression_and_other_sets(self):
        self.write_run("2026-11-11T09:00:00-05:00")
        self.write_run("2026-11-11T09:05:30-05:00", ["E1"], ["E2", "E3"])
        self.write_run("2026-11-11T09:07:00-05:00", ["E2"], ["E1", "E3"])
        self.write_run("2026-11-11T09:08:00-05:00", ["E1"], [], identifier="other")
        self.assertEqual(timing_report(self.log, "probe"),
                         "probe: first run 2026-11-11T09:00:00-05:00\n"
                         "E1: 2026-11-11T09:05:30-05:00 | 5.5 min\n"
                         "E2: 2026-11-11T09:07:00-05:00 | 1.5 min\n"
                         "E3: not yet\nRuns: 3\nTotal active: 7 min")

    def test_break_and_resumed_day_keep_prior_progress(self):
        self.write_run("2026-11-11T09:00:00-05:00")
        self.write_run("2026-11-11T09:10:00-05:00", ["E1"], ["E2", "E3"])
        self.write_run("2026-11-11T09:20:00-05:00", ["E1"], ["E2", "E3"])
        self.write_run("2026-11-11T09:40:00-05:00", ["E1", "E2"], ["E3"])
        self.write_run("2026-11-12T09:40:00-05:00", ["E1", "E2"], ["E3"])
        self.write_run("2026-11-12T09:45:00-05:00", ["E1", "E2", "E3"], [])
        output = timing_report(self.log, "probe")
        self.assertIn("E2: 2026-11-11T09:40:00-05:00 | 30 min", output)
        self.assertIn("E3: 2026-11-12T09:45:00-05:00 | 5 min (plus a break of 1440 min)", output)
        self.assertTrue(output.endswith("Runs: 6\nTotal active: 45 min"))

    def test_long_exercise_counts_every_failing_run(self):
        for minute in range(0, 35, 5):
            self.write_run(f"2026-11-11T09:{minute:02d}:00-05:00")
        self.write_run("2026-11-11T09:35:00-05:00", ["E1"], ["E2", "E3"])
        self.assertEqual(timing_report(self.log, "probe"),
                         "probe: first run 2026-11-11T09:00:00-05:00\n"
                         "E1: 2026-11-11T09:35:00-05:00 | 35 min\n"
                         "E2: not yet\nE3: not yet\nRuns: 8\nTotal active: 35 min")

    def test_break_inside_exercise_keeps_active_time_on_both_sides(self):
        self.write_run("2026-11-11T09:00:00-05:00")
        self.write_run("2026-11-11T09:05:00-05:00")
        self.write_run("2026-11-11T10:40:00-05:00")
        self.write_run("2026-11-11T10:45:30-05:00", ["E1"], ["E2", "E3"])
        output = timing_report(self.log, "probe")
        self.assertIn("E1: 2026-11-11T10:45:30-05:00 | 10.5 min (plus a break of 95 min)", output)
        self.assertTrue(output.endswith("Runs: 4\nTotal active: 10.5 min"))

    def test_runs_after_last_new_pass_count_active_time_but_not_breaks(self):
        self.write_run("2026-11-11T09:00:00-05:00")
        self.write_run("2026-11-11T09:05:00-05:00", ["E1"], ["E2", "E3"])
        self.write_run("2026-11-11T09:10:00-05:00")
        self.write_run("2026-11-11T10:45:00-05:00")
        self.write_run("2026-11-11T10:50:30-05:00", ["E1"], ["E2", "E3"])
        output = timing_report(self.log, "probe")
        self.assertIn("E1: 2026-11-11T09:05:00-05:00 | 5 min", output)
        self.assertTrue(output.endswith("Still working: 10.5 min since the last new pass\n"
                                        "Runs: 5\nTotal active: 15.5 min"))

    def test_break_only_after_last_pass_has_no_still_working_line(self):
        self.write_run("2026-11-11T09:00:00-05:00", ["E1"], ["E2", "E3"])
        self.write_run("2026-11-12T09:00:00-05:00", ["E1"], ["E2", "E3"])
        output = timing_report(self.log, "probe")
        self.assertIn("E1: 2026-11-11T09:00:00-05:00 | 0 min", output)
        self.assertNotIn("Still working:", output)
        self.assertTrue(output.endswith("Total active: 0 min"))

    def test_active_time_before_any_pass_is_in_total(self):
        self.write_run("2026-11-11T09:00:00-05:00")
        self.write_run("2026-11-11T09:05:00-05:00")
        self.write_run("2026-11-11T10:40:00-05:00")
        self.assertEqual(timing_report(self.log, "probe"),
                         "probe: first run 2026-11-11T09:00:00-05:00\n"
                         "E1: not yet\nE2: not yet\nE3: not yet\nRuns: 3\nTotal active: 5 min")

    def test_numeric_display_uses_chronological_events_and_simultaneous_passes(self):
        # Deliberately write the first run last, and complete E10 before E2.
        self.write_run("2026-11-11T09:05:00-05:00", ["E10"], ["E2", "E3"])
        self.write_run("2026-11-11T09:10:00-05:00", ["E10", "E3", "E2"], [])
        self.write_run("2026-11-11T09:00:00-05:00", [], ["E2", "E3", "E10"])
        output = timing_report(self.log, "probe")
        self.assertIn("E2: 2026-11-11T09:10:00-05:00 | 5 min", output)
        self.assertIn("E3: 2026-11-11T09:10:00-05:00 | passed in the same run as E2", output)
        self.assertIn("E10: 2026-11-11T09:05:00-05:00 | 5 min", output)
        self.assertLess(output.index("E2:"), output.index("E10:"))
        self.assertNotIn("E1:", output)
        self.assertNotIn("Still working:", output)
        self.assertTrue(output.endswith("Total active: 10 min"))

    def test_offset_change_and_exact_break_boundary(self):
        self.write_run("2026-11-01T01:50:00-04:00", [], ["E1"])
        self.write_run("2026-11-01T01:10:00-05:00", ["E1"], [])
        self.assertIn("| 20 min", timing_report(self.log, "probe"))
        self.assertIn("| 0 min (plus a break of 20 min)", timing_report(self.log, "probe", 19))

    def test_fractional_gaps_sum_to_whole_minutes(self):
        for second in range(0, 60, 10):
            self.write_run(f"2026-11-11T09:00:{second:02d}-05:00")
        self.write_run("2026-11-11T09:01:00-05:00", ["E1"], ["E2", "E3"])
        output = timing_report(self.log, "probe")
        self.assertIn("E1: 2026-11-11T09:01:00-05:00 | 1 min", output)
        self.assertTrue(output.endswith("Total active: 1 min"))

    def test_malformed_lines_are_skipped(self):
        good = {"time": "2026-11-11T09:00:00-05:00", "set": "probe",
                "passed": [], "failed": ["E1"], "total": 1}
        invalid = [None, [], 42, "text", {}, {**good, "time": "bad"},
                   {**good, "time": "2026-11-11T09:00:00"}, {**good, "time": None},
                   {**good, "passed": "E1"}, {**good, "failed": [1]},
                   {**good, "failed": ["not an exercise"]}, {**good, "total": True},
                   {**good, "total": 2}, {**good, "passed": ["E1"]}]
        self.log.write_bytes(b"broken json\n\xff\n" + b"".join(
            (json.dumps(entry) + "\n").encode("utf-8") for entry in invalid))
        self.write_run(good["time"], [], ["E1"])
        self.assertEqual(timing_report(self.log, "probe"),
                         "probe: first run 2026-11-11T09:00:00-05:00\n"
                         "E1: not yet\nRuns: 1\nTotal active: 0 min")

    def test_empty_missing_and_no_matching_set(self):
        self.assertEqual(timing_report(self.log, "probe"), "No data for probe.")
        self.log.touch()
        self.assertEqual(timing_report(self.log, "probe"), "No data for probe.")
        self.write_run("2026-11-11T09:00:00-05:00", identifier="other")
        self.assertEqual(timing_report(self.log, "probe"), "No data for probe.")

    def test_cli_file_and_break_options_and_missing_file_exit_zero(self):
        command = [sys.executable, str(ROOT / "tools/ft_times.py"), "probe",
                   "--file", str(self.log), "--break-minutes", "3"]
        missing = subprocess.run(command, cwd=self.temporary.name, capture_output=True, text=True)
        self.assertEqual((missing.returncode, missing.stdout, missing.stderr), (0, "No data for probe.\n", ""))
        self.write_run("2026-11-11T09:00:00-05:00", [], ["E1"])
        self.write_run("2026-11-11T09:05:00-05:00", ["E1"], [])
        result = subprocess.run(command, cwd=self.temporary.name, capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertIn("| 0 min (plus a break of 5 min)", result.stdout)


class ReportChecks(unittest.TestCase):
    """The report's counting logic can also be checked before pytest is installed."""
    def setUp(self):
        spec = importlib.util.spec_from_file_location("ft_report_under_test", ROOT / "tools/ft_report.py")
        self.plugin = importlib.util.module_from_spec(spec)
        fake_pytest = SimpleNamespace(hookimpl=lambda **kwargs: lambda function: function)
        with patch.dict(sys.modules, {"pytest": fake_pytest}):
            spec.loader.exec_module(self.plugin)
        self.temporary = tempfile.TemporaryDirectory(prefix="fasttrack report ")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def finish(self, state, paths=(), exitstatus=0):
        destination = self.work / "report.json"
        config = SimpleNamespace(_ft_report=state, args=paths, getoption=lambda option: str(destination),
                                 pluginmanager=SimpleNamespace(getplugin=lambda name: None))
        session = SimpleNamespace(config=config, exitstatus=exitstatus)
        output = io.StringIO()
        with redirect_stdout(output), patch.dict("os.environ", {"FT_REPORT_MODE": ""}):
            self.plugin.pytest_sessionfinish(session, exitstatus)
        return json.loads(destination.read_text(encoding="utf-8")), output.getvalue()

    def test_multiple_tests_require_all_passes(self):
        path = str(self.work / "test_station.py")
        report, output = self.finish({
            "items": {"one": {"name": "test_e1_low", "path": path},
                      "two": {"name": "test_e1_high", "path": path},
                      "three": {"name": "test_e2_reading", "path": path}},
            "results": {"one": True, "two": False, "three": True}, "errors": [],
            "failures": [{"nodeid": "two", "message": "AssertionError: above the limit"}],
        })
        self.assertEqual((report["passed"], report["total"], report["exitstatus"]), (1, 2, 1))
        self.assertIn("FAIL E1: AssertionError: above the limit", output)
        self.assertTrue(output.rstrip().endswith("Exercises: 1 / 2 passed"))

    def test_import_error_recovers_names_from_disk(self):
        source = self.work / "test_station.py"
        source.write_text("import missing_driver\ndef test_e1_reading():\n    pass\ndef test_e2_limit():\n    pass\n", encoding="utf-8")
        report, output = self.finish({"items": {}, "results": {}, "errors": ["ImportError: missing driver"], "failures": []}, [str(source)], 2)
        self.assertEqual((report["passed"], report["total"]), (0, 2))
        self.assertIn("Your code could not be loaded:", output)
        self.assertTrue(output.rstrip().endswith("Exercises: 0 / 2 passed"))

    def test_unknown_total(self):
        report, output = self.finish({"items": {}, "results": {}, "errors": ["SyntaxError: invalid syntax"], "failures": []}, exitstatus=2)
        self.assertIsNone(report["total"])
        self.assertTrue(output.rstrip().endswith("Exercises: 0 / ? passed"))

    def test_plain_test_is_a_check(self):
        report, output = self.finish({"items": {"one": {"name": "test_station", "path": str(self.work / "test_station.py")}},
                                      "results": {"one": True}, "errors": [], "failures": []})
        self.assertEqual((report["kind"], report["passed"], report["total"]), ("Checks", 1, 1))
        self.assertTrue(output.rstrip().endswith("Checks: 1 / 1 passed"))

@unittest.skipUnless(importlib.util.find_spec("pytest"), "Install requirements.txt to run pytest integration checks")
class PipelineChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fasttrack scaffold ")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.repo = self.work / "exercise repo"
        self.solutions = self.work / "reference repo"
        for directory in (self.repo / "sets", self.repo / "gates", self.solutions):
            directory.mkdir(parents=True)
        for filename in ("__init__.py", "ft_report.py", "verify_sets.py"):
            self.write(f"tools/{filename}", (ROOT / "tools" / filename).read_text(encoding="utf-8"))
        self.write("gates/conftest.py", (ROOT / "gates" / "conftest.py").read_text(encoding="utf-8"))
        self.write("capstone/chassis/__init__.py", "")
        self.set_dir = self.repo / "sets" / "probe"
        self.write("sets/probe/conftest.py", "from pathlib import Path\nimport sys\nsys.path.insert(0, str(Path(__file__).resolve().parent))\n")
        self.write("sets/probe/starter/__init__.py", "")
        self.write("sets/probe/starter/probe.py", "def reading():\n    raise NotImplementedError('E1: return a reading')\n")
        self.write("sets/probe/tests/test_probe.py", "from starter.probe import reading\ndef test_e1_reading():\n    assert reading() == 42\n")
        reference = self.solutions / "sets/probe/starter/probe.py"
        reference.parent.mkdir(parents=True)
        reference.write_text("def reading():\n    return 42\n", encoding="utf-8")

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def verify(self, identifier="probe", *options):
        return subprocess.run([sys.executable, str(self.repo / "tools/verify_sets.py"), identifier,
                               "--solutions", str(self.solutions), *options], cwd=self.work,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    def report(self):
        return run_report(self.repo, [self.set_dir], self.work)

    def learner(self, environment=None, *options):
        env = os.environ.copy()
        env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="", PYTHONPATH=str(self.repo),
                   FT_REPORT_MODE="", FT_NO_LOG="")
        env.update(environment or {})
        return subprocess.run([sys.executable, "-m", "pytest", str(self.set_dir), "-p", "tools.ft_report",
                               "-q", "--no-header", *options], cwd=self.work, env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_learner_appends_one_private_log_entry_per_run(self):
        self.write("sets/probe/pytest.ini", "[pytest]\n")
        self.write("sets/probe/tests/test_probe.py", "def test_e10_reading():\n    assert False\n"
                   "def test_e2_low():\n    pass\ndef test_e2_high():\n    pass\n")
        for count in (1, 2):
            result = self.learner()
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertTrue(result.stdout.rstrip().endswith("Exercises: 1 / 2 passed"))
            lines = (self.repo / ".ft-progress.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), count)
            entry = json.loads(lines[-1])
            self.assertEqual(set(entry), {"time", "set", "passed", "failed", "total"})
            self.assertEqual({key: value for key, value in entry.items() if key != "time"},
                             {"set": "probe", "passed": ["E2"], "failed": ["E10"], "total": 2})
            self.assertIsNotNone(datetime.fromisoformat(entry["time"]).utcoffset())
            self.assertRegex(entry["time"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")

    def test_progress_logging_exclusions(self):
        log = self.repo / ".ft-progress.jsonl"
        self.report()  # --ft-report-json verifier run
        self.assertFalse(log.exists())
        for env in ({"FT_REPORT_MODE": "checks"}, {"FT_NO_LOG": "1"}, {"FT_NO_LOG": "0"}):
            with self.subTest(env=env):
                self.learner(env)
                self.assertFalse(log.exists())
        self.learner({}, "--ft-report-json=")  # Presence alone suppresses logging.
        self.assertFalse(log.exists())
        self.write("sets/probe/tests/test_probe.py", "# No exercises collected.\n")
        self.learner()
        self.assertFalse(log.exists())
        self.write("sets/probe/tests/test_probe.py", "def test_e1_reading():\n    pass\n")
        self.write("sets/probe/conftest.py", "raise RuntimeError('cannot collect')\n")
        self.learner()
        self.assertFalse(log.exists())

    def test_logging_oserror_preserves_output_and_exit_status(self):
        log = self.repo / ".ft-progress.jsonl"
        for body in ("pass", "assert False"):
            with self.subTest(body=body):
                self.write("sets/probe/tests/test_probe.py", f"def test_e1_reading():\n    {body}\n")
                disabled = self.learner({"FT_NO_LOG": "1"})
                log.mkdir()
                try:
                    unwritable = self.learner()
                finally:
                    log.rmdir()
                self.assertEqual((unwritable.stdout, unwritable.stderr, unwritable.returncode),
                                 (disabled.stdout, disabled.stderr, disabled.returncode))

    def test_interrupted_phase_never_passes(self):
        for phase in ("setup", "call", "teardown"):
            with self.subTest(phase=phase):
                self.write("sets/probe/tests/test_probe.py", "import pytest\n"
                           "@pytest.fixture\ndef station():\n"
                           + ("    raise KeyboardInterrupt('setup interrupted')\n" if phase == "setup" else "")
                           + "    yield\n"
                           + ("    raise KeyboardInterrupt('teardown interrupted')\n" if phase == "teardown" else "")
                           + "def test_e1_reading(station):\n"
                           + ("    raise KeyboardInterrupt('call interrupted')\n" if phase == "call" else "    pass\n"))
                report = self.report()
                self.assertEqual((report["passed"], report["total"]), (0, 1), report["output"])
                self.assertNotEqual(report["returncode"], 0)
                self.assertNotIn("PASS E1", report["output"])
                self.assertTrue(report["output"].rstrip().endswith("Exercises: 0 / 1 passed"))

    def test_failure_keeps_learner_traceback_and_captured_output(self):
        self.write("sets/probe/starter/probe.py", "import sys\ndef reading():\n"
                   "    print('diagnostic: channel 7')\n"
                   "    print('instrument warning', file=sys.stderr)\n"
                   "    print('extra diagnostic\\n' * 100)\n"
                   "    raise ValueError('bad reading')\n")
        self.write("sets/probe/tests/test_probe.py", "from starter.probe import reading\n"
                   "import pytest\nimport sys\n@pytest.fixture\ndef station():\n"
                   "    print('setup diagnostic', file=sys.stderr)\n    yield\n"
                   "    print('teardown diagnostic', file=sys.stderr)\n"
                   "def test_e1_reading(station):\n    assert reading() == 42\n")
        report = self.report()
        output = report["output"]
        self.assertEqual((report["passed"], report["total"]), (0, 1))
        self.assertIn("FAIL E1: ValueError: bad reading", output)
        self.assertIn("test_e1_reading", output)
        self.assertIn("probe.py:6", output)
        self.assertIn("test_probe.py:10", output)
        self.assertLess(output.index("probe.py:6"), output.index("test_probe.py:10"))
        self.assertIn("raise ValueError('bad reading')", output)
        self.assertIn("diagnostic: channel 7", output)
        self.assertIn("instrument warning", output)
        self.assertIn("setup diagnostic", output)
        self.assertIn("teardown diagnostic", output)
        self.assertIn("truncated", output)
        self.assertLess(len(output), 3500)
        self.assertTrue(output.rstrip().endswith("Exercises: 0 / 1 passed"))

    def test_initial_conftest_import_errors_recover_exercises(self):
        self.write("sets/probe/conftest.py",
                   (self.set_dir / "conftest.py").read_text(encoding="utf-8")
                   + "from starter.probe import reading\n")
        self.write("sets/probe/tests/test_probe.py", "from starter.probe import reading\n"
                   "def test_e1_reading():\n    reading()\n"
                   "def test_e2_reading():\n    reading()\n"
                   "def test_e2_limit():\n    reading()\n")
        for code, error in (("def reading(:\n", "SyntaxError"),
                            ("from missing_station_module import reading\n", "ModuleNotFoundError")):
            with self.subTest(error=error):
                self.write("sets/probe/starter/probe.py", code)
                report = self.report()
                self.assertEqual((report["passed"], report["total"], report["returncode"]), (0, 2, 1))
                self.assertTrue(report["errors"])
                self.assertIn("Your code could not be loaded:", report["output"])
                self.assertIn(error, report["output"])
                self.assertTrue(report["output"].rstrip().endswith("Exercises: 0 / 2 passed"))

    def test_stub_reference_and_repeat(self):
        result = self.verify("probe", "--repeat", "2")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("starter: 0 / 1; reference: 1 / 1 (2 runs)", result.stdout)
        print(result.stdout.strip())

    def test_reject_unexpected_exception(self):
        self.write("sets/probe/starter/probe.py", "def reading():\n    raise ValueError('wrong starter')\n")
        result = self.verify()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("ValueError", result.stdout)

    def test_already_complete_metadata(self):
        self.write("sets/probe/.verify.json", '{"starter_expect": "all"}')
        self.write("sets/probe/starter/probe.py", "def reading():\n    return 42\n")
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("starter: 1 / 1; reference: 1 / 1", result.stdout)

    def test_import_error_recovers_exercise_names(self):
        self.write("sets/probe/starter/probe.py", "from missing_station_module import reading\n")
        self.write("sets/probe/tests/test_probe.py", "from starter.probe import reading\ndef test_e1_reading():\n    reading()\ndef test_e2_reading():\n    reading()\n")
        report = self.report()
        self.assertEqual((report["passed"], report["total"], report["returncode"]), (0, 2, 1))
        self.assertTrue(report["errors"])
        self.assertIn("Your code could not be loaded:", report["output"])
        self.assertTrue(report["output"].rstrip().endswith("Exercises: 0 / 2 passed"))

    def test_import_error_without_names(self):
        self.write("sets/probe/tests/test_probe.py", "import missing_station_module\n")
        report = self.report()
        self.assertIsNone(report["total"])
        self.assertTrue(report["output"].rstrip().endswith("Exercises: 0 / ? passed"))

    def test_grouping_includes_teardown_failure(self):
        self.write("sets/probe/tests/test_probe.py", "import pytest\n@pytest.fixture\ndef station():\n    yield\n    raise RuntimeError('station did not close')\n@pytest.mark.parametrize('reading', [1, 2, 3])\ndef test_e1_reading(reading, station):\n    assert reading > 0\ndef test_e2_reading():\n    assert True\n")
        report = self.report()
        self.assertEqual((report["passed"], report["total"]), (1, 2))
        self.assertIn("station did not close", report["output"])
        self.assertNotIn("short test summary", report["output"])

    def test_plain_tests_are_checks_and_skip_is_unfinished(self):
        self.write("sets/probe/tests/test_probe.py", "import pytest\ndef test_reading():\n    assert True\n@pytest.mark.skip(reason='needs a station')\ndef test_other():\n    assert True\n")
        report = self.report()
        self.assertEqual((report["kind"], report["passed"], report["total"], report["returncode"]), ("Checks", 1, 2, 1))

    def test_cumulative_gates(self):
        for number in (1, 2):
            self.write(f"gates/b{number}/test_b{number}.py", f"from chassis.reading import reading\ndef test_e{number}_reading():\n    assert reading() == 42\n")
        reference = self.solutions / "capstone/chassis/reading.py"
        reference.parent.mkdir(parents=True)
        reference.write_text("def reading():\n    return 42\n", encoding="utf-8")
        result = self.verify("b2", "--repeat", "2")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("bare capstone: 0 / 2; reference: 2 / 2 (2 runs)", result.stdout)

    def test_cpp_hook(self):
        import verify_sets

        starter = "int reading() { return -1; }\n"
        reference = "int reading() { return 42; }\n"
        self.write("sets/probe/starter/probe.cpp", starter)
        self.write("sets/probe/tests/test_probe.cpp", "#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN\n")
        (self.solutions / "sets/probe/starter/probe.cpp").write_text(reference, encoding="utf-8")
        failed = {"passed": 0, "total": 1, "returncode": 1, "errors": [], "output": "FAIL E1"}
        passed = {"passed": 1, "total": 1, "returncode": 0, "errors": [], "output": "PASS E1"}
        for name, reports, expected, message, sources in (
            ("repeat", [failed, passed, passed], True,
             "starter: 0 / 1; reference: 1 / 1 (2 runs)", [starter, reference]),
            ("completed starter", [passed], False, "starter: 1 / 1 (expected none)", [starter]),
            ("failed reference", [failed, passed, failed], False,
             "reference run 2: 0 / 1", [starter, reference]),
        ):
            with self.subTest(name=name):
                compiled = []

                def compile_command(command, **kwargs):
                    self.assertEqual(command[0], "mock-c++")
                    for argument in command[1:]:
                        if Path(argument).name == "probe.cpp":
                            compiled.append(Path(argument).read_text(encoding="utf-8"))
                    return subprocess.CompletedProcess(command, 0, "", "")

                output = io.StringIO()
                with patch.object(verify_sets, "cpp_compiler", return_value=("mock-c++", False, {})) as compiler, \
                     patch.object(verify_sets.subprocess, "run", side_effect=compile_command) as commands, \
                     patch.object(verify_sets, "run_cpp_report", side_effect=reports) as report, \
                     patch.object(verify_sets, "run_report") as python_report, redirect_stdout(output):
                    result = verify_sets.verify_set(self.repo, self.solutions, "probe", 2, False)
                self.assertEqual(result, expected)
                self.assertIn(message, output.getvalue())
                self.assertEqual(compiled, sources)
                self.assertEqual(commands.call_count, 3 * len(sources))
                self.assertEqual(report.call_count, len(reports))
                compiler.assert_called_once_with()
                python_report.assert_not_called()
        self.assertEqual((self.set_dir / "starter/probe.cpp").read_text(encoding="utf-8"), starter)


if __name__ == "__main__":
    unittest.main()
