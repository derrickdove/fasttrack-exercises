"""HTTP endpoints for a chassis test station's operator status page."""
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class Status(BaseModel):
    """The station name and its current operating state."""

    station: str
    state: Literal["IDLE", "RUNNING", "FAULT"]


class Run(BaseModel):
    """One completed test run; started_at is a UTC timestamp in seconds."""

    run_id: str
    station: str
    state: Literal["PASS", "FAIL"]
    started_at: int


app = FastAPI()
current_status = Status(station="CHASSIS-01", state="IDLE")
runs: dict[str, Run] = {}


@app.get("/health")
def health() -> dict[str, bool]:
    """E1: Return the health response with HTTP 200."""
    raise NotImplementedError("E1: return the operator service's health response")


@app.get("/status")
def get_status() -> Status:
    """E2: Return the current station status with HTTP 200."""
    raise NotImplementedError("E2: return current_status")


@app.post("/status")
def set_status(status: Status) -> Status:
    """E2: Replace current_status with the validated body and return it."""
    raise NotImplementedError("E2: replace the module's current_status and return it")


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> Run:
    """E3: Return a stored run, or HTTP 404 with detail 'Run not found'."""
    raise NotImplementedError("E3: find the run or raise HTTPException with status 404")


@app.get("/runs")
def list_runs(state: str | None = None) -> list[Run]:
    """E4: Filter by exact state, then sort by started_at descending, stably."""
    raise NotImplementedError("E4: filter runs and return them newest first")
