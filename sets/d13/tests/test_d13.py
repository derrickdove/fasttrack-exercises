from copy import deepcopy
import logging
import re
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from starter.reporting import (
    failures_by_channel,
    get_station_logger,
    summarize,
    read_junit,
)


@pytest.fixture
def logger_names(tmp_path):
    names = [f"d13.{tmp_path.name}.station", f"d13.{tmp_path.name}.backup"]
    yield names
    for name in names:
        logger = logging.getLogger(name)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()


def flush(logger):
    for handler in logger.handlers:
        handler.flush()


def test_e1_levels_and_line_format(tmp_path, logger_names):
    path = tmp_path / "station.log"
    name = logger_names[0]
    logger = get_station_logger(name, path)
    assert isinstance(logger, logging.Logger), "return the configured logging.Logger"
    for level in (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL):
        logger.log(level, "CH1 reading %s", "µV")
    flush(logger)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4, "record INFO through CRITICAL, omitting DEBUG"
    for line, level in zip(lines, ("INFO", "WARNING", "ERROR", "CRITICAL")):
        pattern = (
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} "
            + re.escape(f"{level} {name}: CH1 reading µV")
        )
        assert re.fullmatch(pattern, line), f"unexpected log format: {line!r}"
    assert logger.level == logging.INFO, "set the named logger's level to INFO"
    assert logger.propagate is False, "station events must not propagate to parent loggers"
    assert len(logger.handlers) == 1, "install one file handler"
    assert isinstance(logger.handlers[0], logging.FileHandler)
    assert logger.handlers[0].level == logging.INFO, "set the file handler's level to INFO"


def test_e1_repeated_setup_does_not_duplicate_events(tmp_path, logger_names):
    path = tmp_path / "run.log"
    first = get_station_logger(logger_names[0], path)
    first.info("before setup again")
    second = get_station_logger(logger_names[0], path)
    third = get_station_logger(logger_names[0], path)
    third.info("after setup again")
    flush(third)
    assert first is second is third, "reuse the logger associated with this name"
    assert len(third.handlers) == 1, "repeated setup must not accumulate handlers"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, "each event must appear once, including after repeated setup"
    assert lines[0].endswith(": before setup again")
    assert lines[1].endswith(": after setup again")


def test_e1_appends_to_existing_file_with_string_path(tmp_path, logger_names):
    path = tmp_path / "operator log.log"
    path.write_text("previous run retained\n", encoding="utf-8")
    logger = get_station_logger(logger_names[0], str(path))
    logger.info("new run")
    flush(logger)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, "append the event without deleting the previous run"
    assert lines[0] == "previous run retained"
    assert lines[1].endswith(": new run")


def test_e1_station_names_have_independent_files(tmp_path, logger_names):
    first_path = tmp_path / "primary.log"
    second_path = tmp_path / "backup.log"
    first = get_station_logger(logger_names[0], first_path)
    second = get_station_logger(logger_names[1], second_path)
    first.info("primary connected")
    second.warning("backup disconnected")
    flush(first)
    flush(second)
    first_lines = first_path.read_text(encoding="utf-8").splitlines()
    second_lines = second_path.read_text(encoding="utf-8").splitlines()
    assert len(first_lines) == len(second_lines) == 1, "keep station files independent"
    assert first_lines[0].endswith(f"INFO {logger_names[0]}: primary connected")
    assert second_lines[0].endswith(f"WARNING {logger_names[1]}: backup disconnected")


def test_e2_counts_every_check_on_repeated_channels():
    results = [
        {"channel": "CH1", "status": status, "message": "voltage check"}
        for status in ("PASS", "FAIL", "PASS", "ERROR", "FAIL")
    ]
    got = summarize(results)
    assert got == {"counts": {"PASS": 2, "FAIL": 2, "ERROR": 1}, "overall": "ERROR"}
    assert type(got) is dict and type(got["counts"]) is dict, "return ordinary dictionaries"


@pytest.mark.parametrize(
    "statuses, expected",
    [
        (["PASS"], "PASS"),
        (["FAIL"], "FAIL"),
        (["ERROR"], "ERROR"),
        (["FAIL", "PASS", "PASS"], "FAIL"),
        (["PASS", "PASS", "FAIL"], "FAIL"),
        (["ERROR", "FAIL", "PASS"], "ERROR"),
        (["PASS", "FAIL", "ERROR"], "ERROR"),
    ],
)
def test_e2_worst_status_is_severity_not_order_or_frequency(statuses, expected):
    results = [{"channel": "CH4", "status": status, "message": "check"} for status in statuses]
    got = summarize(results)
    assert got["overall"] == expected, f"for {statuses}, worst status must be {expected}"
    assert set(got["counts"]) == set(statuses), "include only statuses actually observed"


def test_e2_empty_run():
    assert summarize([]) == {"counts": {}, "overall": "ERROR"}, "no results cannot establish a passing run"


def test_e2_preserves_input_and_does_not_share_counts():
    results = [{"channel": "CH2", "status": "PASS", "message": "ready", "reading": 4.2}]
    before = deepcopy(results)
    first = summarize(results)
    assert results == before, "summary must not modify the check records"
    first["counts"]["PASS"] = 99
    assert summarize(results) == {"counts": {"PASS": 1}, "overall": "PASS"}, "each call gets fresh counts"


def test_e3_groups_fail_and_error_messages_in_channel_order():
    results = [
        {"channel": "CH1", "status": "FAIL", "message": "voltage low"},
        {"channel": "CH2", "status": "PASS", "message": "ready"},
        {"channel": "CH3", "status": "ERROR", "message": "no reply"},
        {"channel": "CH1", "status": "PASS", "message": "recovered"},
        {"channel": "CH1", "status": "ERROR", "message": "timeout"},
        {"channel": "CH3", "status": "FAIL", "message": "current high"},
    ]
    got = failures_by_channel(results)
    assert got == {"CH1": ["voltage low", "timeout"], "CH3": ["no reply", "current high"]}
    assert type(got) is dict, "return a plain dict rather than a defaultdict"


@pytest.mark.parametrize("results", [[], [{"channel": "CH2", "status": "PASS", "message": "ready"}]])
def test_e3_omits_channels_without_failures(results):
    assert failures_by_channel(results) == {}, "empty and all-PASS runs have no failure channels"


def test_e3_keeps_duplicate_and_empty_messages():
    results = [
        {"channel": "CH1", "status": status, "message": message}
        for status, message in (("FAIL", "low"), ("ERROR", ""), ("FAIL", "low"))
    ]
    assert failures_by_channel(results) == {"CH1": ["low", "", "low"]}, "retain every failure message"


def test_e3_preserves_input_and_uses_separate_lists():
    results = [
        {"channel": "CH1", "status": "FAIL", "message": "low"},
        {"channel": "CH2", "status": "ERROR", "message": "offline"},
    ]
    before = deepcopy(results)
    got = failures_by_channel(results)
    assert results == before, "grouping must not modify check records"
    got["CH1"].append("operator note")
    assert got["CH2"] == ["offline"], "each channel needs its own list"
    assert failures_by_channel(results) == {"CH1": ["low"], "CH2": ["offline"]}, "calls must be independent"


@pytest.fixture(scope="module")
def e4_ready(tmp_path_factory):
    path = tmp_path_factory.mktemp("junit-probe") / "empty.xml"
    path.write_text("<testsuites />", encoding="utf-8")
    read_junit(path)  # Unfinished E4 fails with its own NotImplementedError.


@pytest.fixture(scope="module")
def run_station(tmp_path_factory, e4_ready):
    base = tmp_path_factory.mktemp("station-junit")
    cache = {}

    def run(voltage=None):
        if voltage in cache:
            return cache[voltage]
        directory = base / f"run-{len(cache)}"
        directory.mkdir()
        source = Path(__file__).resolve().parents[1] / "starter" / "station_checks.py"
        shutil.copyfile(source, directory / "station_checks.py")
        (directory / "pytest.ini").write_text("[pytest]\njunit_family = xunit1\n", encoding="utf-8")
        if voltage is not None:
            # Change the supplied measurements to check the learner's actual assertion.
            hook = (
                "def pytest_collection_modifyitems(items):\n"
                "    for item in items:\n"
                "        if item.callspec.params['station_ready'] == 'ready':\n"
                f"            item.callspec.params['voltage'] = {voltage!r}\n"
            )
            (directory / "conftest.py").write_text(hook, encoding="utf-8")
        env = os.environ.copy()
        env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_ADDOPTS="", PYTHONDONTWRITEBYTECODE="1")
        env.pop("PYTHONPATH", None)
        env.pop("PYTEST_PLUGINS", None)
        command = [sys.executable, "-m", "pytest", "station_checks.py", "-q", "--tb=short",
                   "-c", "pytest.ini", "-p", "no:cacheprovider", "--junitxml=station.xml"]
        completed = subprocess.run(command, cwd=directory, env=env, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", timeout=10)
        output = completed.stdout + completed.stderr
        report = directory / "station.xml"
        assert report.exists(), f"pytest must produce its JUnit report:\n{output}"
        assert completed.returncode == 1, f"This lab deliberately includes failing checks:\n{output}"
        cases = list(ET.parse(report).getroot().iter("testcase"))
        assert [case.attrib["name"] for case in cases] == [
            "test_e4_voltage[nominal]", "test_e4_voltage[undervoltage]", "test_e4_voltage[offline]",
        ], f"Use the three required parametrize rows and ids:\n{output}"
        cache[voltage] = report, cases
        return cache[voltage]

    return run


def test_e4_station_cases_have_outcomes_and_metadata(run_station):
    _, cases = run_station()
    assert all(cases[0].find(tag) is None for tag in ("error", "failure", "skipped")), "nominal must pass"
    failure = cases[1].find("failure")
    assert failure is not None, "undervoltage must fail an assertion"
    error = cases[2].find("error")
    assert error is not None and "RuntimeError: station offline" in error.attrib["message"], "offline must fail in fixture setup"
    for case in cases:
        property_nodes = case.findall("properties/property")
        assert len(property_nodes) == 2, "record each metadata property exactly once"
        properties = {prop.attrib["name"]: prop.attrib["value"] for prop in property_nodes}
        assert properties == {"station_id": "CHASSIS-A1", "serial_number": "SN-0042"}, (
            "Record both properties before fixture setup can fail."
        )


@pytest.mark.parametrize("voltage, tag", [(5.0, None), (4.8, None), (5.2, None), (4.0, "failure"), (5.3, "failure")])
def test_e4_station_asserts_the_measurement(run_station, voltage, tag):
    _, cases = run_station(voltage)
    for case in cases[:2]:
        if tag is None:
            assert all(case.find(child) is None for child in ("error", "failure", "skipped")), "in-limit measurements must pass"
        else:
            assert case.find(tag) is not None, "assert the actual voltage; do not fail a case just because of its id"
    assert cases[2].find("error") is not None, "offline must still be a fixture error"


def test_e4_reads_real_pytest_report(run_station):
    report, _ = run_station()
    assert read_junit(report) == [
        {"name": f"test_e4_voltage[{case_id}]", "outcome": outcome,
         "properties": {"station_id": "CHASSIS-A1", "serial_number": "SN-0042"}}
        for case_id, outcome in (("nominal", "PASS"), ("undervoltage", "FAIL"), ("offline", "ERROR"))
    ], "read the generated report, including metadata on the failed setup"


@pytest.mark.parametrize("root", ["testsuite", "testsuites"])
@pytest.mark.parametrize("string_path", [False, True])
def test_e4_reads_properties_statuses_and_document_order(tmp_path, e4_ready, root, string_path):
    suite = """<testsuite><testcase name="voltage[high]">
      <properties><property name="station_id" value="A&amp;B"/>
      <property name="serial_number" value="SN-µ"/></properties><failure message="high"/>
      </testcase><testcase name="setup"><error message="offline"/></testcase>
      <testcase name="optional"><skipped message="not fitted"/></testcase>
      <testcase name="ready"/></testsuite>"""
    xml = suite if root == "testsuite" else f"<testsuites>{suite}<testsuite><testcase name='last'/></testsuite></testsuites>"
    path = tmp_path / "station report.xml"
    path.write_text(xml, encoding="utf-8")
    original = path.read_bytes()
    expected = [
        {"name": "voltage[high]", "outcome": "FAIL", "properties": {"station_id": "A&B", "serial_number": "SN-µ"}},
        {"name": "setup", "outcome": "ERROR", "properties": {}},
        {"name": "optional", "outcome": "SKIP", "properties": {}},
        {"name": "ready", "outcome": "PASS", "properties": {}},
    ]
    if root == "testsuites":
        expected.append({"name": "last", "outcome": "PASS", "properties": {}})
    assert read_junit(str(path) if string_path else path) == expected, "use each testcase's children and properties"
    assert path.read_bytes() == original, "reading must not modify the XML report"


@pytest.mark.parametrize("xml", ["<testsuites/>", "<testsuite/>", "<testsuites><testsuite/></testsuites>"])
def test_e4_empty_report(tmp_path, e4_ready, xml):
    path = tmp_path / "empty.xml"
    path.write_text(xml, encoding="utf-8")
    assert read_junit(path) == [], "an empty report contains no test outcomes"


def test_e4_xml_and_file_errors_reach_caller(tmp_path, e4_ready):
    with pytest.raises(OSError):
        read_junit(tmp_path / "missing.xml")
    path = tmp_path / "broken.xml"
    path.write_text("<testsuites>", encoding="utf-8")
    with pytest.raises(ET.ParseError):
        read_junit(path)


def test_e1_file_error_reaches_caller(tmp_path, logger_names):
    with pytest.raises(OSError):
        get_station_logger(logger_names[0], tmp_path)
