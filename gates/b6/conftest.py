"""Gate-owned fixtures; learner modules load only when a check runs."""

from importlib import import_module, reload
import json
import os
from pathlib import Path
import re

import pytest


@pytest.fixture
def config():
    return import_module("chassis.config")


@pytest.fixture
def web():
    # Each check starts from a fresh module, without accessing private state.
    return reload(import_module("chassis.web"))


@pytest.fixture
def station_text():
    return (Path(__file__).parent / "data" / "station.toml").read_text(encoding="utf-8")


@pytest.fixture
def station_file(tmp_path):
    def write(content):
        path = tmp_path / "station config.toml"
        path.write_text(content, encoding="utf-8")
        return path
    return write


@pytest.fixture
def capstone_root():
    default = Path(__file__).resolve().parents[2] / "capstone"
    return Path(os.environ.get("FT_CAPSTONE", str(default)))


@pytest.fixture
def docker_instructions(capstone_root):
    text = (capstone_root / "Dockerfile").read_text(encoding="utf-8")
    text = re.sub(r"\\\r?\n", " ", text)
    instructions = []
    for line in text.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            parts = line.strip().split(None, 1)
            opcode, argument = parts[0].upper(), parts[1] if len(parts) > 1 else ""
            if opcode in {"RUN", "CMD", "ENTRYPOINT"} and argument.startswith("["):
                argument = " ".join(json.loads(argument))
            instructions.append((opcode, argument.strip()))
    return instructions


@pytest.fixture
def invokes_chassis():
    def check(command):
        if command.lstrip().startswith("["):
            command = " ".join(json.loads(command))
        return re.search(
            r"(?:^|[\s\"'])[^\s\"']*python(?:3(?:\.12)?)?[\"']?\s+-m\s+chassis\b",
            command,
        ) is not None
    return check


@pytest.fixture
def playbook(capstone_root):
    import yaml
    return yaml.safe_load((capstone_root / "deploy" / "ansible" / "playbook.yml").read_text(encoding="utf-8"))
