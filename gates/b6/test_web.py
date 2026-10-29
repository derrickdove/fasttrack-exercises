"""Exercise the public FastAPI app in process, without a network server."""

from importlib import import_module
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


def test_status_defaults_to_unknown_station_and_idle(web):
    assert isinstance(web.app, FastAPI)
    with TestClient(web.app) as client:
        response = client.get("/status")
        assert response.status_code == 200
        assert response.json() == {"station": "unknown", "state": "IDLE"}


def test_set_status_replaces_station_and_state_on_each_call(web):
    with TestClient(web.app) as client:
        for station, state in [("bench-1", "RUNNING"), ("bench-2", "FAIL")]:
            web.set_status(station, state)
            response = client.get("/status")
            assert response.status_code == 200
            assert response.json() == {"station": station, "state": state}


def test_latest_report_returns_404_before_any_report_is_registered(web):
    with TestClient(web.app) as client:
        assert client.get("/results/latest").status_code == 404


@pytest.mark.parametrize("value,status", [(24.1, "PASS"), (float("nan"), "ERROR")],
                         ids=["finite-reading", "nan-reading"])
def test_latest_report_serves_block_two_json_report_unchanged(web, tmp_path, value, status):
    models = import_module("chassis.models")
    themis = import_module("chassis.themis")
    report = import_module("chassis.report")
    result = themis.check(models.Measurement("bus_voltage", value, "V"),
                          models.Limit("bus_voltage", 22.0, 30.0, "V"))
    path = tmp_path / "report.json"
    report.write_json_report([result], path, {"station": "Banc électrique"})
    document = json.loads(path.read_text(encoding="utf-8"),
                          parse_constant=lambda token: pytest.fail(f"invalid JSON constant: {token}"))
    assert document["summary"]["overall"] == status
    assert document["results"][0]["status"] == status
    assert document["results"][0]["value"] == (None if status == "ERROR" else value)
    web.set_latest_report(document)
    with TestClient(web.app) as client:
        response = client.get("/results/latest")
        assert response.status_code == 200
        received = json.loads(response.content,
                              parse_constant=lambda token: pytest.fail(f"invalid JSON constant: {token}"))
        assert received == document


def test_latest_report_replaces_previous_report_and_accepts_empty_dictionary(web):
    with TestClient(web.app) as client:
        for document in [{"meta": {"station": "first"}, "results": []},
                         {"meta": {"station": "second"}, "results": [{"value": None}]}, {}]:
            web.set_latest_report(document)
            response = client.get("/results/latest")
            assert response.status_code == 200, "an empty registered dict is still a report"
            assert response.json() == document
