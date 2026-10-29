"""Inspect deployment text; never execute Docker, systemd, or Ansible."""

import configparser
from pathlib import PurePosixPath
import re
import shlex


class _UnitOptions(dict):
    def __setitem__(self, key, value):
        # ConfigParser stores lists while reading, then joins them into strings.
        if key in {"after", "wants", "wantedby"} and isinstance(value, list) and key in self:
            value = self[key] + value
        super().__setitem__(key, value)


def _read_unit(capstone_root):
    unit = configparser.ConfigParser(interpolation=None, strict=False, dict_type=_UnitOptions)
    unit.read_string((capstone_root / "deploy" / "chassis-telemetry.service").read_text(encoding="utf-8"))
    return unit


def _all_tasks(tasks):
    for task in tasks:
        yield task
        for section in ("block", "rescue", "always"):
            yield from _all_tasks(task.get(section, []))


def _installs_unit(task, module):
    arguments = task[module]
    if isinstance(arguments, str):
        arguments = dict(word.split("=", 1) for word in shlex.split(arguments) if "=" in word)
    arguments = {**(arguments or {}), **task.get("args", {})}
    destination = arguments.get("dest", "")
    if destination.endswith("/"):
        destination += PurePosixPath(arguments.get("src", "")).name
    return PurePosixPath(destination).name == "chassis-telemetry.service"


def test_systemd_unit_has_network_dependencies_and_install_target(capstone_root):
    unit = _read_unit(capstone_root)
    assert unit["Unit"]["Description"].strip(), "describe the service"
    assert "network-online.target" in unit["Unit"]["After"].split()
    assert "network-online.target" in unit["Unit"]["Wants"].split()
    assert "multi-user.target" in unit["Install"]["WantedBy"].split()


def test_systemd_service_runs_chassis_with_restart_policy_and_non_root_user(capstone_root, invokes_chassis):
    unit = _read_unit(capstone_root)
    service = unit["Service"]
    assert service["Type"] == "simple"
    assert invokes_chassis(service["ExecStart"]), "ExecStart must run python -m chassis"
    assert service["Restart"] == "on-failure"
    assert service["RestartSec"].strip(), "include RestartSec"
    assert service["User"].strip() and service["User"].strip() not in {"root", "0"}


def test_dockerfile_uses_python_312_slim_and_copies_project_and_installs_tools(docker_instructions):
    bases = [word for op, arg in docker_instructions if op == "FROM"
             for word in arg.split() if not word.startswith("--")]
    assert any(re.fullmatch(r"python:3\.12(?:\.\d+)?-slim(?:-[\w.-]+)?(?:@sha256:[0-9a-f]+)?", base)
               for base in bases), "use a Python 3.12 slim base"
    assert any(op == "WORKDIR" and arg for op, arg in docker_instructions)
    assert any(op == "COPY" and arg for op, arg in docker_instructions)
    assert any(op == "RUN" and re.search(r"\bpip(?:3(?:\.12)?)?\s+install\b", arg)
               for op, arg in docker_instructions), "install tools with pip (python -m pip is also valid)"


def test_dockerfile_invokes_chassis_and_finishes_with_non_root_user(docker_instructions, invokes_chassis):
    commands = [arg for op, arg in docker_instructions if op in {"CMD", "ENTRYPOINT"}]
    assert any(invokes_chassis(command) for command in commands), "CMD or ENTRYPOINT must run python -m chassis"
    users = [arg for op, arg in docker_instructions if op == "USER"]
    assert users, "declare the runtime USER"
    assert users[-1].split(":", 1)[0].strip() not in {"", "root", "0"}


def test_ansible_has_one_privileged_station_play_with_install_and_service_tasks(playbook):
    assert isinstance(playbook, list) and len(playbook) == 1, "write one play"
    play = playbook[0]
    assert play["hosts"] == "test_stations"
    assert play["become"] is True
    tasks = list(_all_tasks(play["tasks"]))
    assert any(_installs_unit(task, module) for task in tasks
               for module in ("ansible.builtin.copy", "ansible.builtin.template") if module in task), (
        "install chassis-telemetry.service with copy or template; copying only the project is insufficient"
    )
    assert any("ansible.builtin.pip" in task or "ansible.builtin.command" in task for task in tasks)
    services = [task[module] for task in tasks for module in
                ["ansible.builtin.systemd", "ansible.builtin.systemd_service"] if module in task]
    assert any(service.get("enabled") is True and service.get("state") == "started"
               and service.get("daemon_reload") is True for service in services), (
        "enable and start the service with daemon_reload: true"
    )


def test_inventory_has_test_stations_group_with_at_least_one_host(capstone_root):
    text = (capstone_root / "deploy" / "ansible" / "inventory.ini").read_text(encoding="utf-8")
    in_group = False
    hosts = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("["):
            in_group = line == "[test_stations]"
        elif in_group:
            hosts.append(line)
    assert hosts, "add at least one host under [test_stations]"
