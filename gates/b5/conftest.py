"""Gate-owned fixtures; import learner modules only when each check runs."""

from importlib import import_module
from pathlib import Path
import os
import subprocess
import sys
import shutil

import pytest


@pytest.fixture
def models():
    return import_module("chassis.models")


@pytest.fixture
def executor():
    return import_module("chassis.executor")


@pytest.fixture
def themis():
    return import_module("chassis.themis")


@pytest.fixture
def cli():
    return import_module("chassis.cli")


@pytest.fixture
def report():
    return import_module("chassis.report")


@pytest.fixture
def input_files(tmp_path):
    data = Path(__file__).parent / "data"
    limits = tmp_path / "station limits.csv"
    measurements = tmp_path / "station measurements.csv"
    shutil.copyfile(data / "limits.csv", limits)
    shutil.copyfile(data / "measurements.csv", measurements)
    return limits, measurements


@pytest.fixture
def recorded_step(executor, models):
    def make(name, events, *, fail_at=None, error=None, value=24.0):
        def record(phase):
            events.append(f"{name}:{phase}")
            if phase == fail_at:
                raise error if error is not None else RuntimeError("bench connection lost")

        def setup():
            record("setup")

        def run():
            record("run")
            return [models.Measurement("bus_voltage", value, "V")]

        def teardown():
            record("teardown")

        return executor.TestStep(name, run, setup, teardown)

    return make


@pytest.fixture
def bus_limits(models):
    return {"bus_voltage": models.Limit("bus_voltage", 22.0, 30.0, "V")}


@pytest.fixture
def command():
    def build(paths):
        limits, measurements = paths
        return ["check", "--limits", str(limits), "--measurements", str(measurements)]

    return build


@pytest.fixture
def assert_input_error():
    def assert_error(code, stderr):
        assert code == 3
        assert len(stderr.splitlines()) == 1, stderr
        assert stderr.startswith("error: "), stderr
        assert "Traceback" not in stderr

    return assert_error


@pytest.fixture
def run_module():
    def invoke(args):
        # gates/conftest.py has already selected the learner or isolated reference.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(sys.path)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run([sys.executable, "-m", "chassis", *args], env=env,
                              capture_output=True, text=True, encoding="utf-8", timeout=5)

    return invoke
