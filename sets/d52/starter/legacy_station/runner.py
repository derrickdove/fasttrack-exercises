"""Entry point for a small, established station procedure.

Call run_station with connected drivers and a list of Step objects. It
collects readings in list order and returns rows suitable for a report.
It never enables an output: the caller owns instrument setup and shutdown.
"""

from dataclasses import dataclass

from .base import Driver
from .limits import check_limits, validate_limits


# Older operator screens read this shared dictionary after each run.
LAST_REPORT: dict[str, object] = {}


@dataclass(frozen=True)
class Step:
    """One named check, its instrument key, band, and number of readings.

    Each driver reports its own documented unit. All limits for a step must
    use that unit. The instrument key selects a driver from the caller's
    dictionary; it is a station label, not an instrument model name.
    """

    name: str
    instrument: str
    low: float
    high: float
    samples: int = 1


@dataclass(frozen=True)
class Result:
    """One report row; an ERROR row has no measured value."""

    name: str
    value: float | None
    status: str
    detail: str


def run_station(drivers: dict[str, Driver], steps: list[Step]) -> list[Result]:
    """Validate the plan, average each step's readings, and record results.

    An invalid plan raises ValueError before taking any measurements.
    An instrument exception records ERROR for that step, then the next step
    still runs. A failed band check records FAIL. Order is preserved and
    an empty plan produces an empty report. Samples must be integers.
    """
    names: set[str] = set()
    for step in steps:
        if not step.name or step.name in names:
            raise ValueError("step names must be nonempty and unique")
        names.add(step.name)
        if step.instrument not in drivers:
            raise ValueError(f"unknown instrument: {step.instrument}")
        validate_limits(step.low, step.high)
        if not 1 <= step.samples <= 20:
            raise ValueError("samples outside station budget")

    results: list[Result] = []
    for step in steps:
        values: list[float] = []
        try:
            driver = drivers[step.instrument]
            for _ in range(step.samples):
                value = driver.read()
                values.append(value)
            average = sum(values) / len(values)
            accepted = check_limits(average, step.low, step.high)
            if accepted:
                status = "PASS"
                detail = "within limits"
            else:
                status = "FAIL"
                detail = "outside limits"
            results.append(Result(step.name, average, status, detail))
        except Exception as error:
            results.append(Result(step.name, None, "ERROR", str(error)))

    LAST_REPORT.clear()
    LAST_REPORT["steps"] = len(results)
    LAST_REPORT["passed"] = sum(row.status == "PASS" for row in results)
    LAST_REPORT["failed"] = sum(row.status == "FAIL" for row in results)
    LAST_REPORT["errors"] = sum(row.status == "ERROR" for row in results)
    return results
