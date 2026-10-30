from collections.abc import Iterator

from fastapi.testclient import TestClient
import pytest

from starter.statuspage import Run, Status, app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr("starter.statuspage.current_status", Status(station="CHASSIS-01", state="IDLE"))
    monkeypatch.setattr("starter.statuspage.runs", {})
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def run_store(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> dict[str, Run]:
    records = [
        Run(run_id="run-old", station="B2", state="PASS", started_at=9),
        Run(run_id="run-tie-z", station="B2", state="PASS", started_at=20),
        Run(run_id="run-new", station="A1", state="FAIL", started_at=100),
        Run(run_id="run-tie-a", station="A1", state="FAIL", started_at=20),
    ]
    store = {run.run_id: run for run in records}
    monkeypatch.setattr("starter.statuspage.runs", store)
    return store


def test_e1_health_response(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200, "the operator health check must succeed"
    assert response.json() == {"ok": True}, "health must contain the boolean ok=true"
    assert response.headers["content-type"].startswith("application/json")


def test_e1_repeated_health_reads(client: TestClient) -> None:
    for _ in range(3):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}, "health must stay the same across reads"


def test_e2_initial_station_status(client: TestClient) -> None:
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"station": "CHASSIS-01", "state": "IDLE"}


@pytest.mark.parametrize("state", ["IDLE", "RUNNING", "FAULT"])
@pytest.mark.parametrize("station", ["B2", ""])
def test_e2_publish_and_read_status(client: TestClient, state: str, station: str) -> None:
    payload = {"station": station, "state": state}
    response = client.post("/status", json=payload)
    assert response.status_code == 200, "a valid station status must be accepted"
    assert response.json() == payload, "POST must return the status it stored"
    readback = client.get("/status")
    assert readback.status_code == 200
    assert readback.json() == payload, "GET must show the last accepted status"


def test_e2_latest_post_replaces_status(client: TestClient) -> None:
    for payload in [
        {"station": "A1", "state": "RUNNING"},
        {"station": "B2", "state": "FAULT"},
    ]:
        response = client.post("/status", json=payload)
        assert response.status_code == 200
        assert response.json() == payload
    assert client.get("/status").json() == {"station": "B2", "state": "FAULT"}


@pytest.mark.parametrize("bad_state", ["running", "FAIL", "", None, 7])
def test_e2_reject_invalid_state_without_losing_status(client: TestClient, bad_state: object) -> None:
    accepted = {"station": "B2", "state": "RUNNING"}
    assert client.post("/status", json=accepted).status_code == 200
    response = client.post("/status", json={"station": "A1", "state": bad_state})
    assert response.status_code == 422, f"state {bad_state!r} must fail validation"
    assert response.json().get("detail"), "a validation error should explain the bad body"
    assert client.get("/status").json() == accepted, "invalid input must not replace status"


@pytest.mark.parametrize("payload", [
    {},
    {"station": "A1"},
    {"state": "IDLE"},
    {"station": 5, "state": "IDLE"},
    {"station": None, "state": "IDLE"},
])
def test_e2_require_valid_body_fields(client: TestClient, payload: dict[str, object]) -> None:
    before = client.get("/status").json()
    response = client.post("/status", json=payload)
    assert response.status_code == 422, f"body {payload!r} must fail validation"
    assert client.get("/status").json() == before, "rejected bodies must leave status intact"


@pytest.mark.parametrize("run_id", ["run-old", "run-new", "run-tie-z"])
def test_e3_find_full_run(client: TestClient, run_store: dict[str, Run], run_id: str) -> None:
    response = client.get(f"/runs/{run_id}")
    assert response.status_code == 200, f"stored run {run_id} must be found"
    assert response.json() == run_store[run_id].model_dump(), "return every run field"


@pytest.mark.parametrize("run_id", ["missing", "RUN-NEW", "0"])
def test_e3_missing_run_is_404(client: TestClient, run_store: dict[str, Run], run_id: str) -> None:
    response = client.get(f"/runs/{run_id}")
    assert response.status_code == 404, f"unknown run {run_id!r} must return 404"
    assert response.json() == {"detail": "Run not found"}


def test_e3_read_does_not_consume_run(client: TestClient, run_store: dict[str, Run]) -> None:
    before = {key: run.model_dump() for key, run in run_store.items()}
    for _ in range(2):
        response = client.get("/runs/run-new")
        assert response.status_code == 200
        assert response.json() == before["run-new"]
    assert {key: run.model_dump() for key, run in run_store.items()} == before


def test_e4_all_runs_newest_first(client: TestClient, run_store: dict[str, Run]) -> None:
    response = client.get("/runs")
    expected_ids = ["run-new", "run-tie-z", "run-tie-a", "run-old"]
    assert response.status_code == 200
    assert response.json() == [run_store[key].model_dump() for key in expected_ids], (
        "sort numerically by started_at descending, preserving insertion order for ties"
    )


@pytest.mark.parametrize("state, expected_ids", [
    ("FAIL", ["run-new", "run-tie-a"]),
    ("PASS", ["run-tie-z", "run-old"]),
])
def test_e4_filter_state(client: TestClient, run_store: dict[str, Run], state: str,
                         expected_ids: list[str]) -> None:
    response = client.get("/runs", params={"state": state})
    assert response.status_code == 200
    assert response.json() == [run_store[key].model_dump() for key in expected_ids], (
        f"include only {state} runs, newest first"
    )


@pytest.mark.parametrize("state", ["UNKNOWN", "fail", ""])
def test_e4_unmatched_state_is_empty(client: TestClient, run_store: dict[str, Run], state: str) -> None:
    response = client.get("/runs", params={"state": state})
    assert response.status_code == 200, "unknown filters are valid queries with no matches"
    assert response.json() == [], f"state filter {state!r} must match exactly"


@pytest.mark.parametrize("query", ["/runs", "/runs?state=FAIL"])
def test_e4_empty_store(client: TestClient, query: str) -> None:
    response = client.get(query)
    assert response.status_code == 200
    assert response.json() == [], "an empty station history is an empty JSON list"


def test_e4_listing_leaves_store_unchanged(client: TestClient, run_store: dict[str, Run]) -> None:
    before = [(key, run.model_dump()) for key, run in run_store.items()]
    for query in ["/runs?state=FAIL", "/runs", "/runs?state=PASS", "/runs"]:
        response = client.get(query)
        assert response.status_code == 200
    after = [(key, run.model_dump()) for key, run in run_store.items()]
    assert after == before, "reading must preserve all records and dictionary insertion order"
