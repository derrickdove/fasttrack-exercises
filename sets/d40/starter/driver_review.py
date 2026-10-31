"""E4: Record a review of the supplied driver and its proposed repair."""
from typing import TypedDict


class ReviewFinding(TypedDict):
    """One finding; option letters are defined in the README."""

    file: str
    line: int
    consequence: str
    regression_test: str
    repair_fixed: bool
    repair_reason: str
    comment: str


def review_answers() -> list[ReviewFinding]:
    """Return exactly three findings, each anchored to the original new file."""
    raise NotImplementedError("E4: review the driver diff and assess its repair")
