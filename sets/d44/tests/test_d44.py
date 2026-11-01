"""Inspect files only: no containers, remote hosts, or external processes."""
import json
from pathlib import Path
import re
import shlex

import pytest
import yaml

STARTER = Path(__file__).resolve().parents[1] / "starter"


def _file(name: str, exercise: int) -> str:
    text = (STARTER / name).read_text(encoding="utf-8")
    if not any(line.strip() and not line.lstrip().startswith("#") for line in text.splitlines()):
        raise NotImplementedError(f"E{exercise}: Fill in starter/{name} using the README contract")
    return text


def _instructions() -> list[tuple[str, str]]:
    instructions = []
    for line in _file("Dockerfile", 1).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            parts = stripped.split(maxsplit=1)
            assert len(parts) == 2, f"Dockerfile instruction needs an argument: {line!r}"
            instructions.append((parts[0].upper(), parts[1]))
    return instructions


def _project_copies(instructions: list[tuple[str, str]]) -> list[int]:
    workdir = ""
    copies = []
    for index, (operation, argument) in enumerate(instructions):
        if operation == "WORKDIR":
            workdir = argument
        elif operation == "COPY":
            args = shlex.split(argument)
            if (workdir.startswith("/") and len(args) == 2 and args[0] == "."
                    and args[1].rstrip("/") in (".", workdir.rstrip("/"))):
                copies.append(index)
    return copies


def _play() -> dict:
    plays = yaml.safe_load(_file("playbook.yml", 2))
    assert isinstance(plays, list) and len(plays) == 1, "Write a YAML list containing exactly one play"
    play = plays[0]
    assert isinstance(play, dict), "A play is a mapping of keys to values"
    assert isinstance(play.get("tasks"), list) and play["tasks"], "The play needs a nonempty tasks list"
    assert all(isinstance(task, dict) and isinstance(task.get("name"), str) and task["name"].strip()
               for task in play["tasks"]), "Every task needs a nonempty name"
    assert all(sum(isinstance(key, str) and key.startswith("ansible.builtin.") for key in task) == 1
               for task in play["tasks"]), "Use separate tasks with exactly one ansible.builtin.* module each"
    return play


def _groups() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    current = ""
    for line in _file("inventory.ini", 3).splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            groups.setdefault(current, [])
        else:
            assert current, "Inventory hosts must follow a [group] header"
            groups[current].append(line.split()[0])
    return groups


def test_e1_base_and_project_copy() -> None:
    instructions = _instructions()
    bases = [arg for op, arg in instructions if op == "FROM"]
    assert instructions[0][0] == "FROM" and len(bases) == 1, "Use one stage starting with FROM"
    assert re.fullmatch(r"python:3\.12(?:\.\d+)?-slim(?:-[a-z0-9]+)?", bases[0]), "Base must be a Python 3.12 slim image"
    workdirs = [arg for op, arg in instructions if op == "WORKDIR"]
    assert workdirs and workdirs[-1].startswith("/"), "Set an absolute WORKDIR"
    assert _project_copies(instructions), "Set an absolute WORKDIR, then COPY the whole project (.) into it"


def test_e1_package_install_and_launch() -> None:
    instructions = _instructions()
    installs = []
    for index, (operation, argument) in enumerate(instructions):
        if operation == "RUN":
            args = shlex.split(argument)
            for prefix in (["pip", "install"], ["python", "-m", "pip", "install"],
                           ["python3", "-m", "pip", "install"]):
                if len(args) > len(prefix) and args[:len(prefix)] == prefix:
                    installs.append((index, args[len(prefix):]))
                    break
    assert installs, "Use RUN pip install PACKAGE or RUN python -m pip install PACKAGE"
    copies = _project_copies(instructions)
    assert all("." not in packages or any(copy < index for copy in copies)
               for index, packages in installs), "COPY the project before installing it with pip install ."

    # Keep the last CMD and ENTRYPOINT in this Dockerfile, regardless of order.
    # A local ENTRYPOINT resets the base image CMD, so inherited CMD is ignored.
    entrypoint = ""
    command = ""
    for operation, argument in instructions:
        if operation == "ENTRYPOINT":
            entrypoint = argument
        elif operation == "CMD":
            command = argument
    assert entrypoint or command, "Provide CMD or ENTRYPOINT"
    entry_args = json.loads(entrypoint) if entrypoint.startswith("[") else shlex.split(entrypoint)
    command_args = json.loads(command) if command.startswith("[") else shlex.split(command)
    if entry_args:
        # Shell-form ENTRYPOINT ignores CMD; exec form receives CMD as arguments.
        if entrypoint.startswith("[") and command and not command.startswith("["):
            command_args = ["/bin/sh", "-c", command]
        args = entry_args + command_args if entrypoint.startswith("[") else entry_args
    else:
        args = command_args
    assert args[:3] in (["python", "-m", "chassis"], ["python3", "-m", "chassis"]), (
        "The effective final CMD/ENTRYPOINT must invoke python -m chassis (optional arguments follow)"
    )


def test_e1_cmd_before_entrypoint_is_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = _file("Dockerfile", 1)
    (tmp_path / "Dockerfile").write_text(
        text + '\nCMD ["-m","chassis"]\nENTRYPOINT ["python"]\n', encoding="utf-8"
    )
    monkeypatch.setitem(globals(), "STARTER", tmp_path)
    test_e1_package_install_and_launch()


def test_e1_nonroot_runtime_user() -> None:
    users = [arg for op, arg in _instructions() if op == "USER"]
    assert users, "Set USER for the operator process"
    user = users[-1].split(":")[0]
    assert user and user.lower() != "root" and not (user.isdecimal() and int(user) == 0), "The final USER must be non-root"


def test_e2_station_target_and_privilege() -> None:
    play = _play()
    assert play.get("hosts") == "test_stations", "Target the test_stations inventory group"
    assert play.get("become") is True, "Use become: true to install the station service"


def test_e2_unit_copy_and_package_install() -> None:
    tasks = _play()["tasks"]
    units = [task[module] for task in tasks for module in ("ansible.builtin.copy", "ansible.builtin.template") if module in task]
    assert any(isinstance(args, dict) and args.get("src") and args.get("dest") == "/etc/systemd/system/chassis-telemetry.service"
               for args in units), "Copy/template the service unit to /etc/systemd/system/chassis-telemetry.service"
    prerequisites = []
    for index, task in enumerate(tasks):
        args = task.get("ansible.builtin.apt")
        if isinstance(args, dict) and args.get("state") == "present":
            names = args.get("name")
            if names == "python3-venv" or (isinstance(names, list) and "python3-venv" in names):
                prerequisites.append(index)
    assert prerequisites, "Install python3-venv with ansible.builtin.apt and state: present"
    packages = [(index, task["ansible.builtin.pip"]) for index, task in enumerate(tasks)
                if "ansible.builtin.pip" in task]
    installs = [index for index, args in packages if isinstance(args, dict) and args.get("name")
                and args.get("virtualenv") == "/opt/chassis/.venv"
                and args.get("virtualenv_command") == "python3 -m venv"]
    assert installs, "Use pip.name with virtualenv: /opt/chassis/.venv and virtualenv_command: python3 -m venv"
    assert any(prerequisite < install for prerequisite in prerequisites for install in installs), (
        "Install python3-venv before the pip task creates the virtual environment"
    )


def test_e2_service_is_started_and_enabled() -> None:
    services = [task[module] for task in _play()["tasks"] for module in (
        "ansible.builtin.systemd", "ansible.builtin.systemd_service"
    ) if module in task]
    assert any(isinstance(args, dict) and args.get("name") in ("chassis-telemetry", "chassis-telemetry.service")
               and args.get("enabled") is True and args.get("state") == "started"
               and args.get("daemon_reload") is True for args in services), "Enable/start chassis-telemetry and reload unit definitions using YAML booleans"


def test_e3_inventory_has_station_and_bench_groups() -> None:
    groups = _groups()
    assert "test_stations" in groups or "test_stations:children" in groups, "Define test_stations directly or through :children"
    assert groups.get("bench"), "The [bench] group needs at least one host alias"


def test_e3_bench_hosts_are_test_stations() -> None:
    groups = _groups()
    stations = set(groups.get("test_stations", []))
    if "bench" in groups.get("test_stations:children", []):
        stations.update(groups.get("bench", []))
    assert stations, "test_stations must resolve to at least one host"
    assert set(groups.get("bench", [])) <= stations, "Every bench host must also belong to test_stations"
