from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import logging
import re

import pytest

from starter.reporting import (
    failures_by_channel,
    get_station_logger,
    summarize,
    write_report,
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
    assert summarize([]) == {"counts": {}, "overall": "PASS"}, "empty runs use the documented default"


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


@pytest.mark.parametrize("string_path", [False, True])
def test_e4_report_shape_summary_and_full_results(tmp_path, string_path):
    results = [
        {"channel": "CH2", "status": "PASS", "message": "ready", "reading": 2.5},
        {"channel": "CH1", "status": "ERROR", "message": "capteur débranché", "details": [1, None]},
        {"channel": "CH1", "status": "FAIL", "message": "voltage low"},
    ]
    meta = {"station": "A1", "operator": "Zoë", "attempt": 2}
    now = datetime(2026, 10, 28, 12, 30, tzinfo=timezone.utc)
    path = tmp_path / "run report.json"
    returned = write_report(results, str(path) if string_path else path, meta, now=now)
    got = json.loads(path.read_text(encoding="utf-8"))
    assert returned is None, "write_report writes a file and returns None"
    assert got == {
        "meta": {**meta, "generated_utc": "2026-10-28T12:30:00+00:00"},
        "summary": {"counts": {"PASS": 1, "ERROR": 1, "FAIL": 1}, "overall": "ERROR"},
        "results": results,
    }, "preserve run metadata and full result records, using the documented report shape"


@pytest.mark.parametrize(
    "now, expected",
    [
        (datetime(2026, 10, 28, 1, 30, 2, 123456, tzinfo=timezone(timedelta(hours=2))),
         "2026-10-27T23:30:02.123456+00:00"),
        (datetime(2026, 10, 28, 23, 45, tzinfo=timezone(timedelta(hours=-3, minutes=-30))),
         "2026-10-29T03:15:00+00:00"),
    ],
)
def test_e4_injected_time_is_converted_to_utc(tmp_path, now, expected):
    path = tmp_path / "report.json"
    write_report([], path, {}, now=now)
    got = json.loads(path.read_text(encoding="utf-8"))
    assert got["meta"]["generated_utc"] == expected, "convert the instant to UTC, preserving fractional seconds"


def test_e4_metadata_copy_overwrites_old_timestamp_without_mutating_inputs(tmp_path):
    results = [{"channel": "CH1", "status": "FAIL", "message": "low", "details": {"v": 1.0}}]
    meta = {"station": "A1", "generated_utc": "old timestamp", "tags": ["acceptance"]}
    before_results, before_meta = deepcopy(results), deepcopy(meta)
    now = datetime(2026, 10, 28, tzinfo=timezone.utc)
    path = tmp_path / "report.json"
    write_report(results, path, meta, now=now)
    got = json.loads(path.read_text(encoding="utf-8"))
    assert results == before_results and meta == before_meta, "do not change caller-owned inputs"
    assert got["meta"] == {**meta, "generated_utc": now.isoformat()}, "replace a stale timestamp in the file copy"


def test_e4_overwrites_existing_report_with_empty_run(tmp_path):
    path = tmp_path / "report.json"
    path.write_text("old report content that is longer than an empty run " * 100, encoding="utf-8")
    now = datetime(2026, 10, 28, tzinfo=timezone.utc)
    write_report([], path, {}, now=now)
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "meta": {"generated_utc": now.isoformat()},
        "summary": {"counts": {}, "overall": "PASS"},
        "results": [],
    }, "replace the old file completely; do not append JSON documents"


def test_e4_default_time_is_current_aware_utc(tmp_path):
    path = tmp_path / "report.json"
    before = datetime.now(timezone.utc)
    write_report([], path, {"station": "A1"})
    after = datetime.now(timezone.utc)
    got = json.loads(path.read_text(encoding="utf-8"))
    timestamp = got["meta"]["generated_utc"]
    parsed = datetime.fromisoformat(timestamp)
    assert timestamp.endswith("+00:00"), "use isoformat with an explicit UTC offset"
    assert before <= parsed <= after, "when now is omitted, use the current UTC instant"


def test_e1_file_error_reaches_caller(tmp_path, logger_names):
    with pytest.raises(OSError):
        get_station_logger(logger_names[0], tmp_path)


def test_e4_file_error_reaches_caller(tmp_path):
    with pytest.raises(OSError):
        write_report([], tmp_path, {}, now=datetime(2026, 10, 28, tzinfo=timezone.utc))
