import csv
from copy import deepcopy
import json
from pathlib import Path

import pytest

from starter.trace import (
    Requirements, Results, coverage, load_requirements, matrix_csv, untested,
)

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def reqs() -> Requirements:
    # Read the fixture independently, so E2-E4 do not depend on a finished E1.
    with (DATA / "requirements.csv").open(encoding="utf-8", newline="") as stream:
        return {row["id"]: dict(row) for row in csv.DictReader(stream)}


@pytest.fixture
def results() -> Results:
    return json.loads((DATA / "results.json").read_text(encoding="utf-8"))


def read_matrix(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.reader(stream))


def test_e1_supplied_station_plan(reqs: Requirements) -> None:
    got = load_requirements(DATA / "requirements.csv")
    assert got == reqs, "Preserve id, text, and all four methods from the plan"
    assert got["REQ-04"]["text"].endswith(", including labels."), "A quoted comma is part of the text"


def test_e1_strip_values_and_accept_reordered_header(tmp_path: Path) -> None:
    path = tmp_path / "station plan.csv"
    path.write_text('method,text,id\n Inspection ,"  Check connector, label  ", R-2 \n', encoding="utf-8")
    got = load_requirements(str(path))
    assert got == {"R-2": {"id": "R-2", "text": "Check connector, label", "method": "Inspection"}}, (
        "Strip field edges, retain interior spaces, and locate columns by name"
    )


def test_e1_header_only_and_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "empty_plan.csv"
    path.write_text("id,text,method\n\n", encoding="utf-8")
    assert load_requirements(path) == {}, "A header-only plan contains no requirements"
    path.write_text("id,text,method\n\nR1,Supply check,Test\n\n", encoding="utf-8")
    assert list(load_requirements(path)) == ["R1"], "Ignore completely empty lines"


@pytest.mark.parametrize("header", [
    "", "id,text\n", "id,text,technique\n", "id,id,method\n",
    "id,text,method,extra\n", " id,text,method\n",
])
def test_e1_reject_invalid_header(tmp_path: Path, header: str) -> None:
    path = tmp_path / "bad_header.csv"
    path.write_text(header, encoding="utf-8")
    with pytest.raises(ValueError):
        load_requirements(path)


@pytest.mark.parametrize("rows", [
    "R1,Check voltage,test\n", "R1,Check voltage,Unknown\n",
    " ,Check voltage,Test\n", "R1,  ,Test\n", "R1,Check voltage, \n",
    "R1,Check voltage\n", "R1,Check voltage,Test,extra\n",
    "R1,Check voltage,Test\n R1 ,Check current,Analysis\n", "   \n",
])
def test_e1_reject_invalid_rows(tmp_path: Path, rows: str) -> None:
    path = tmp_path / "bad_rows.csv"
    path.write_text("id,text,method\n" + rows, encoding="utf-8")
    with pytest.raises(ValueError):
        load_requirements(path)


def test_e1_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_requirements(tmp_path / "missing.csv")


def test_e2_supplied_station_coverage(reqs: Requirements, results: Results) -> None:
    expected = {"verified": ["REQ-01", "REQ-04", "REQ-06"],
                "failed": ["REQ-02"], "not-run": ["REQ-03", "REQ-05"]}
    assert coverage(reqs, results) == expected, "Every known requirement belongs in exactly one group"


@pytest.mark.parametrize("statuses,expected", [
    (["PASS", "PASS"], "verified"), (["PASS", "FAIL"], "failed"),
    (["FAIL", "PASS"], "failed"), (["FAIL", "FAIL"], "failed"),
])
def test_e2_failure_wins_in_either_order(statuses: list[str], expected: str) -> None:
    plan = {"R": {"id": "R", "text": "Supply shall meet limits.", "method": "Test"}}
    evidence = [{"req_id": "R", "test_name": "supply", "status": status} for status in statuses]
    got = coverage(plan, evidence)
    want = {"verified": [], "failed": [], "not-run": []}
    want[expected] = ["R"]
    assert got == want, "Repeated evidence must not duplicate ids or let a pass erase a failure"


def test_e2_no_requirements_or_no_evidence(reqs: Requirements, results: Results) -> None:
    assert coverage({}, results) == {"verified": [], "failed": [], "not-run": []}, (
        "Unknown evidence must not introduce requirements"
    )
    assert coverage(reqs, []) == {"verified": [], "failed": [], "not-run": sorted(reqs)}, (
        "Without evidence, every method is not-run"
    )
    assert coverage({}, []) == {"verified": [], "failed": [], "not-run": []}


def test_e2_sorted_groups_without_mutation(reqs: Requirements, results: Results) -> None:
    plan = dict(reversed(list(reqs.items())))
    evidence = list(reversed(results))
    before = deepcopy((plan, evidence))
    got = coverage(plan, evidence)
    assert got == {"verified": ["REQ-01", "REQ-04", "REQ-06"],
                   "failed": ["REQ-02"], "not-run": ["REQ-03", "REQ-05"]}, (
        "Sort each group independently of plan and evidence order"
    )
    assert (plan, evidence) == before, "Coverage must leave the plan and evidence unchanged"


def test_e3_supplied_test_work_list(reqs: Requirements, results: Results) -> None:
    assert untested(reqs, results) == ["REQ-03"], "The missing Analysis evidence is not an unrun Test"


def test_e3_only_test_method_and_sorted(reqs: Requirements) -> None:
    plan = dict(reversed(list(reqs.items())))
    assert untested(plan, []) == ["REQ-01", "REQ-02", "REQ-03"], (
        "Only Test-method requirements belong on the station's untested list"
    )
    assert untested({}, []) == [], "An empty plan has no untested requirements"


@pytest.mark.parametrize("status", ["PASS", "FAIL"])
def test_e3_any_record_counts_as_run_without_mutation(status: str) -> None:
    plan = {"R": {"id": "R", "text": "Check command timing.", "method": "Test"}}
    evidence = [{"req_id": "R", "test_name": "command", "status": status},
                {"req_id": "OLD", "test_name": "unused", "status": "PASS"}]
    before = deepcopy((plan, evidence))
    assert untested(plan, evidence) == [], "A failure still means that the check ran"
    assert (plan, evidence) == before, "Do not modify the plan or evidence"
    assert untested({}, evidence) == [], "Unknown ids are never added to the work list"


def test_e4_supplied_review_matrix(tmp_path: Path, reqs: Requirements, results: Results) -> None:
    path = tmp_path / "matrix.csv"
    returned = matrix_csv(reqs, results, path)
    assert returned is None, "The export writes a file and returns None"
    assert read_matrix(path) == [
        ["req_id", "method", "test_names", "status"],
        ["REQ-01", "Test", "startup_repeat;startup_voltage", "verified"],
        ["REQ-02", "Test", "command_latency;command_retry", "failed"],
        ["REQ-03", "Test", "", "not-run"],
        ["REQ-04", "Inspection", "harness_visual", "verified"],
        ["REQ-05", "Analysis", "", "not-run"],
        ["REQ-06", "Demonstration", "operator_abort", "verified"],
    ], "Export all four methods with linked names and conservative statuses"


def test_e4_unique_names_and_csv_quoting(tmp_path: Path) -> None:
    plan = {"R": {"id": "R", "text": "Check shields.", "method": "Inspection"}}
    special = 'z \u03a9 shield, "continuity"\ncheck'
    evidence = [
        {"req_id": "R", "test_name": special, "status": "PASS"},
        {"req_id": "R", "test_name": "a_visual", "status": "FAIL"},
        {"req_id": "R", "test_name": special, "status": "PASS"},
        {"req_id": "OLD", "test_name": "ignore_me", "status": "FAIL"},
    ]
    path = tmp_path / "quoted.csv"
    matrix_csv(plan, evidence, str(path))
    assert read_matrix(path) == [["req_id", "method", "test_names", "status"],
                                 ["R", "Inspection", "a_visual;" + special, "failed"]], (
        "Deduplicate and sort names, preserve CSV-sensitive characters, and ignore unknown ids"
    )


def test_e4_empty_plan_overwrites_existing_file(tmp_path: Path, results: Results) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("stale contents that must be replaced", encoding="utf-8")
    matrix_csv({}, results, path)
    assert read_matrix(path) == [["req_id", "method", "test_names", "status"]], (
        "An empty plan must overwrite stale rows and keep only the exact header"
    )


def test_e4_sorted_missing_evidence_without_mutation(tmp_path: Path, reqs: Requirements) -> None:
    plan = dict(reversed(list(reqs.items())))
    evidence: Results = []
    before = deepcopy((plan, evidence))
    path = tmp_path / "not_run.csv"
    matrix_csv(plan, evidence, path)
    expected = [["req_id", "method", "test_names", "status"]]
    expected += [[req_id, plan[req_id]["method"], "", "not-run"] for req_id in sorted(plan)]
    assert read_matrix(path) == expected, "Sort rows and show an empty names field for every unrun method"
    assert (plan, evidence) == before, "Exporting must leave its inputs unchanged"
