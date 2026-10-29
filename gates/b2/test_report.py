"""Block 2 reports through the public result and report interfaces."""

from dataclasses import asdict, replace
import json
from pathlib import Path
from types import ModuleType

import pytest


@pytest.mark.parametrize("string_path", [False, True], ids=["path-object", "path-string"])
def test_json_report_preserves_meta_and_result_fields_and_counts_statuses(
    report: ModuleType, mixed_results: list, tmp_path: Path, string_path: bool,
) -> None:
    path = tmp_path / "station report.json"
    meta = {"station": "Banc \u00e9lectrique", "run": 17, "operator": {"shift": "night"}}
    returned = report.write_json_report(mixed_results, str(path) if string_path else path, meta)
    assert returned is None
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document == {
        "meta": meta,
        "summary": {"total": 3, "pass": 1, "fail": 1, "error": 1, "overall": "ERROR"},
        "results": [{**asdict(result), "status": result.status.value} for result in mixed_results],
    }


@pytest.mark.parametrize("field", ["value", "low", "high"])
@pytest.mark.parametrize("number", [float("nan"), float("inf"), -float("inf")],
                         ids=["nan", "positive-infinity", "negative-infinity"])
def test_json_report_writes_non_finite_result_numbers_as_null(
    report: ModuleType, mixed_results: list, tmp_path: Path, field: str, number: float,
) -> None:
    result = replace(mixed_results[0], **{field: number})
    path = tmp_path / "non-finite.json"
    report.write_json_report([result], path, {})
    document = json.loads(path.read_text(encoding="utf-8"),
                          parse_constant=lambda token: pytest.fail(f"invalid JSON constant: {token}"))
    assert document["results"] == [{**asdict(result), field: None, "status": result.status.value}]
    assert document["summary"] == {"total": 1, "pass": 1, "fail": 0, "error": 0, "overall": "PASS"}


def test_json_report_sorts_keys_recursively_and_indents_two_spaces(
    report: ModuleType, mixed_results: list, tmp_path: Path,
) -> None:
    path = tmp_path / "report.json"
    report.write_json_report(mixed_results, path, {"z": 1, "a": {"z": 2, "a": 3}})
    text = path.read_text(encoding="utf-8")
    document = json.loads(text)
    # Either JSON spelling of Unicode is valid; trailing newline is optional.
    expected = [json.dumps(document, sort_keys=True, indent=2, ensure_ascii=ascii_only) for ascii_only in (True, False)]
    assert text.rstrip("\n") in expected, "use sorted keys and indent=2"


def test_json_report_empty_results_has_zero_counts_and_error(report: ModuleType, tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    report.write_json_report([], path, {})
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "meta": {}, "results": [],
        "summary": {"total": 0, "pass": 0, "fail": 0, "error": 0, "overall": "ERROR"},
    }


def test_summary_text_counts_statuses_and_lists_only_non_pass_results(
    report: ModuleType, mixed_results: list,
) -> None:
    assert report.summary_text(mixed_results).splitlines() == [
        "OVERALL: ERROR (1 pass, 1 fail, 1 error)",
        "FAIL supply_current: above high bound 3.0",
        "ERROR temperature: not measured",
    ]


def test_summary_text_all_pass_has_only_overall_line(report: ModuleType, mixed_results: list) -> None:
    assert report.summary_text(mixed_results[:1]).splitlines() == [
        "OVERALL: PASS (1 pass, 0 fail, 0 error)"
    ]


def test_summary_text_empty_results_is_error(report: ModuleType) -> None:
    assert report.summary_text([]).splitlines() == ["OVERALL: ERROR (0 pass, 0 fail, 0 error)"]


@pytest.mark.parametrize("count,expected", [(1, "PASS"), (2, "FAIL")], ids=["pass", "fail"])
def test_json_report_overall_without_errors(
    report: ModuleType, mixed_results: list, tmp_path: Path, count: int, expected: str,
) -> None:
    path = tmp_path / "report.json"
    report.write_json_report(mixed_results[:count], path, {})
    assert json.loads(path.read_text(encoding="utf-8"))["summary"]["overall"] == expected
