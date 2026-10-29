"""Author regressions: run separately from the cumulative learner checks."""

from copy import deepcopy
from pathlib import Path
import runpy

import pytest


GATE = runpy.run_path(str(Path(__file__).parents[1] / "b6" / "test_deploy.py"))
ANSIBLE_CHECK = GATE["test_ansible_has_one_privileged_station_play_with_install_and_service_tasks"]
UNIT_NAME = "chassis-telemetry.service"
UNIT = """[Unit]
Description=Chassis tester
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
ExecStart=python -m chassis check
Restart=on-failure
RestartSec=5
User=chassis
[Install]
WantedBy=multi-user.target
"""


@pytest.mark.parametrize("key,required", [
    ("After", "network-online.target"), ("Wants", "network-online.target"),
    ("WantedBy", "multi-user.target"),
])
@pytest.mark.parametrize("extra_first", [False, True])
def test_repeated_unit_dependencies_pass_both_checks(tmp_path, key, required, extra_first):
    original = f"{key}={required}"
    extra = f"{key}=local-fs.target"
    replacement = f"{extra}\n{original}" if extra_first else f"{original}\n{extra}"
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / UNIT_NAME).write_text(UNIT.replace(original, replacement), encoding="utf-8")
    GATE["test_systemd_unit_has_network_dependencies_and_install_target"](tmp_path)
    GATE["test_systemd_service_runs_chassis_with_restart_policy_and_non_root_user"](
        tmp_path, lambda command: command == "python -m chassis check",
    )


@pytest.fixture
def playbook():
    return [{"hosts": "test_stations", "become": True, "tasks": [
        {"ansible.builtin.copy": {"src": "../../", "dest": "/opt/chassis/"}},
        {"ansible.builtin.copy": {"src": f"../{UNIT_NAME}",
                                  "dest": f"/etc/systemd/system/{UNIT_NAME}"}},
        {"ansible.builtin.pip": {"name": "fastapi"}},
        {"ansible.builtin.systemd": {"enabled": True, "state": "started", "daemon_reload": True}},
    ]}]


@pytest.mark.parametrize("section", ["block", "rescue", "always", "nested"])
def test_ansible_finds_grouped_tasks(playbook, section):
    tasks = playbook[0]["tasks"]
    if section == "nested":
        grouped = {"block": [{"block": [tasks[0]], "rescue": [tasks[1]], "always": tasks[2:]}]}
    else:
        grouped = {section: tasks}
        if section != "block":
            grouped["block"] = [{"ansible.builtin.debug": {"msg": "station"}}]
    playbook[0]["tasks"] = [{"name": "Deploy station", **grouped}]
    ANSIBLE_CHECK(playbook)


@pytest.mark.parametrize("module", ["ansible.builtin.copy", "ansible.builtin.template"])
@pytest.mark.parametrize("style", ["mapping", "free-form", "args", "directory"])
def test_ansible_unit_install_accepts_argument_styles(playbook, module, style):
    arguments = {"src": f"../{UNIT_NAME}", "dest": f"/etc/systemd/system/{UNIT_NAME}"}
    if style == "directory":
        arguments["dest"] = "/etc/systemd/system/"
    elif module == "ansible.builtin.template":
        arguments["src"] += ".j2"
    if style == "free-form":
        task = {module: " ".join(f"{key}={value}" for key, value in arguments.items())}
    elif style == "args":
        task = {module: None, "args": arguments}
    else:
        task = {module: arguments}
    playbook[0]["tasks"][1] = task
    ANSIBLE_CHECK(playbook)


def test_ansible_rejects_project_copy_without_unit_install(playbook):
    ANSIBLE_CHECK(playbook)
    project_only = deepcopy(playbook)
    del project_only[0]["tasks"][1]
    with pytest.raises(AssertionError):
        ANSIBLE_CHECK(project_only)
