"""Link station evidence to verification requirements."""
import csv
from pathlib import Path

Requirements = dict[str, dict[str, str]]
Results = list[dict[str, str]]


def load_requirements(path: str | Path) -> Requirements:
    """Read and validate the id, text, method CSV; key rows by stripped id."""
    raise NotImplementedError("E1: Read and validate the station requirements CSV")


def coverage(reqs: Requirements, results: Results) -> dict[str, list[str]]:
    """Group sorted known ids as verified, failed, or not-run; FAIL wins."""
    raise NotImplementedError("E2: Match evidence to requirements and summarize status")


def untested(reqs: Requirements, results: Results) -> list[str]:
    """Return sorted Test-method ids with no PASS or FAIL evidence."""
    raise NotImplementedError("E3: Find Test requirements with no recorded check")


def matrix_csv(reqs: Requirements, results: Results, path: str | Path) -> None:
    """Write req_id,method,test_names,status rows in sorted requirement order."""
    raise NotImplementedError("E4: Export the station traceability matrix as CSV")
