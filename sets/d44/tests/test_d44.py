"""Inspect files only: no containers, remote hosts, or external processes."""
import json
from pathlib import Path
import re
import shlex

import pytest
import yaml

from starter.deploycheck import idempotent_tasks
from starter.deploycheck import role_problems

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


def _write_playbook(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "station.yml"
    path.write_text(text, encoding="utf-8")
    return path


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

    # Docker keeps the last of each instruction; a new ENTRYPOINT clears an earlier CMD.
    entrypoint = ""
    command = ""
    for operation, argument in instructions:
        if operation == "ENTRYPOINT":
            entrypoint, command = argument, ""
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
    packages = [task["ansible.builtin.pip"] for task in tasks if "ansible.builtin.pip" in task]
    commands = [task["ansible.builtin.command"] for task in tasks if "ansible.builtin.command" in task]
    has_pip = any(isinstance(args, dict) and args.get("name") for args in packages)
    has_command = any((isinstance(args, str) and args.strip()) or (isinstance(args, dict) and args.get("cmd"))
                      for args in commands)
    assert has_pip or has_command, "Install a package with pip.name or a nonempty command/cmd"


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


def test_e4_reports_both_modules_in_document_order(tmp_path: Path) -> None:
    path = _write_playbook(tmp_path, """
- hosts: test_stations
  tasks:
    - name: Read station identity
      ansible.builtin.command: chassis-id
    - name: Read station revision
      ansible.builtin.shell:
        cmd: cat /opt/chassis/revision
    - name: Copy limits
      ansible.builtin.copy:
        src: limits.csv
        dest: /opt/chassis/limits.csv
- hosts: bench
  tasks:
    - name: Read station identity
      ansible.builtin.command: chassis-id
""")
    got = idempotent_tasks(path)
    assert got == ["Read station identity", "Read station revision", "Read station identity"], f"Keep play/task order and duplicate names, got {got!r}"


@pytest.mark.parametrize("module", ["ansible.builtin.command", "ansible.builtin.shell"])
@pytest.mark.parametrize("guard", ["creates", "removes"])
def test_e4_accepts_file_guards_in_args_or_module(tmp_path: Path, module: str, guard: str) -> None:
    path = _write_playbook(tmp_path, f"""
- hosts: bench
  tasks:
    - name: Guard inside module parameters
      {module}:
        cmd: station-init
        {guard}: /opt/chassis/ready
    - name: Guard in task args
      {module}: station-init
      args:
        {guard}: /opt/chassis/ready
""")
    assert idempotent_tasks(path) == [], "creates/removes may be in module parameters or task args"


@pytest.mark.parametrize("value", ["false", "true", "'station_result.rc == 0'", "[]"])
def test_e4_changed_when_is_checked_by_presence(tmp_path: Path, value: str) -> None:
    path = _write_playbook(tmp_path, f"""
- hosts: bench
  tasks:
    - name: Read telemetry status
      ansible.builtin.command: telemetry-status
      changed_when: {value}
    - name: Read driver status
      ansible.builtin.shell: driver-status
      changed_when: {value}
""")
    assert idempotent_tasks(path) == [], "Even changed_when: false is an explicit reporting rule"


def test_e4_unrelated_keys_do_not_guard_tasks(tmp_path: Path) -> None:
    path = _write_playbook(tmp_path, """
- hosts: bench
  changed_when: false
  tasks:
    - name: Probe supply
      ansible.builtin.command:
        cmd: probe-psu
      args:
        chdir: /opt/chassis
      register: supply_result
    - name: Probe meter
      ansible.builtin.shell: probe-dmm
      when: station_online
    - name: Guarded initialization
      ansible.builtin.command: station-init
      args:
        creates: /opt/chassis/ready
""")
    assert idempotent_tasks(path) == ["Probe supply", "Probe meter"], "Only task-local guard keys count; register/when/chdir are not guards"


@pytest.mark.parametrize("text", ["", "# station not commissioned yet\n", "[]", "- hosts: bench\n", "- hosts: bench\n  tasks: []\n"])
def test_e4_empty_inputs_and_string_paths(tmp_path: Path, text: str) -> None:
    path = _write_playbook(tmp_path, text)
    assert idempotent_tasks(str(path)) == [], "Empty documents, missing tasks, and empty task lists have no unsafe tasks"


def test_e4_file_and_yaml_errors_propagate(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        idempotent_tasks(tmp_path / "missing.yml")
    path = _write_playbook(tmp_path, "- hosts: [bench\n")
    with pytest.raises(yaml.YAMLError):
        idempotent_tasks(path)


@pytest.mark.parametrize(("folder", "expected"), [
    ("good", []),
    ("missing_tasks", ["tasks/main.yml: missing"]),
    ("bad_shapes", [
        "defaults/main.yml: expected a mapping",
        "tasks/main.yml: expected a list",
    ]),
    ("notify_mismatch", [
        "handlers/main.yml: handler 'Restart station' is never notified",
        "tasks/main.yml: task 1 has no name",
        "tasks/main.yml: task 2 notifies unknown handler 'Reload driver'",
    ]),
])
def test_e5_supplied_roles(folder: str, expected: list[str]) -> None:
    role_dir = STARTER.parent / "data/roles" / folder
    got = role_problems(role_dir)
    assert got == expected, f"For role {folder}, expected {expected!r}, got {got!r}"


@pytest.mark.parametrize("with_optional_files", [False, True])
def test_e5_empty_task_list_and_optional_files(tmp_path: Path, with_optional_files: bool) -> None:
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks/main.yml").write_text("[]", encoding="utf-8")
    if with_optional_files:
        (tmp_path / "defaults").mkdir()
        (tmp_path / "defaults/main.yml").write_text("{}", encoding="utf-8")
        (tmp_path / "handlers").mkdir()
        (tmp_path / "handlers/main.yml").write_text("[]", encoding="utf-8")
    assert role_problems(tmp_path) == [], "Empty lists/mappings are valid; optional files may be absent"
    (tmp_path / "tasks/main.yml").unlink()
    (tmp_path / "tasks/probe.yml").write_text(
        "- name: Probe station\n  notify: Missing handler\n", encoding="utf-8"
    )
    assert role_problems(tmp_path) == [
        "tasks/main.yml: missing",
        "tasks/probe.yml: task 1 notifies unknown handler 'Missing handler'",
    ], "Missing main.yml must not stop checks; without handlers every notification is unknown"


@pytest.mark.parametrize("text", ["", "# not filled in", "null", "[]", "telemetry", "9200", "false"])
def test_e5_defaults_must_be_mapping(tmp_path: Path, text: str) -> None:
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks/main.yml").write_text("[]", encoding="utf-8")
    (tmp_path / "defaults").mkdir()
    (tmp_path / "defaults/main.yml").write_text(text, encoding="utf-8")
    assert role_problems(tmp_path) == ["defaults/main.yml: expected a mapping"], (
        f"Present defaults must load as a dict, even when empty/comment-only: {text!r}"
    )


@pytest.mark.parametrize("text", ["", "# no tasks yet", "null", "{}", "station", "false", "9200"])
def test_e5_every_direct_yml_task_file_must_be_list(tmp_path: Path, text: str) -> None:
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks/main.yml").write_text("[]", encoding="utf-8")
    (tmp_path / "tasks/calibrate.yml").write_text(text, encoding="utf-8")
    (tmp_path / "tasks/notes.txt").write_text("not YAML: [", encoding="utf-8")
    (tmp_path / "tasks/nested").mkdir()
    (tmp_path / "tasks/folder.yml").mkdir()
    (tmp_path / "tasks/nested/ignored.yml").write_text("{}", encoding="utf-8")
    assert role_problems(tmp_path) == ["tasks/calibrate.yml: expected a list"], (
        "Check every direct tasks/*.yml file, and ignore other extensions and nested folders"
    )


def test_e5_names_notifications_and_sorted_messages(tmp_path: Path) -> None:
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks/main.yml").write_text("""
- name: Install settings
  notify: [Restart telemetry, Restart telemetry]
- name: null
  notify: [restart telemetry, Missing driver, Missing driver]
- name: '   '
- name: 17
- ansible.builtin.command: chassis-id
""", encoding="utf-8")
    (tmp_path / "tasks/extra.yml").write_text("""
- name: Calibrate station
  notify: Reload driver
- name: Calibrate station
  notify: Missing driver
""", encoding="utf-8")
    (tmp_path / "handlers").mkdir()
    (tmp_path / "handlers/main.yml").write_text("""
- name: Reload driver
- name: Restart telemetry
- name: Unused handler
""", encoding="utf-8")
    expected = [
        "handlers/main.yml: handler 'Unused handler' is never notified",
        "tasks/extra.yml: task 2 notifies unknown handler 'Missing driver'",
        "tasks/main.yml: task 2 has no name",
        "tasks/main.yml: task 2 notifies unknown handler 'Missing driver'",
        "tasks/main.yml: task 2 notifies unknown handler 'restart telemetry'",
        "tasks/main.yml: task 3 has no name",
        "tasks/main.yml: task 4 has no name",
        "tasks/main.yml: task 5 has no name",
    ]
    got = role_problems(tmp_path)
    assert got == expected, f"Keep per-task diagnostics, match names exactly, and sort: {got!r}"
    assert role_problems(tmp_path) == expected, "Repeated calls must not retain notifications from earlier roles"
    (tmp_path / "tasks/main.yml").write_text("[]", encoding="utf-8")
    (tmp_path / "tasks/extra.yml").write_text("[]", encoding="utf-8")
    assert role_problems(tmp_path) == [
        "handlers/main.yml: handler 'Reload driver' is never notified",
        "handlers/main.yml: handler 'Restart telemetry' is never notified",
        "handlers/main.yml: handler 'Unused handler' is never notified",
    ], "Each call must collect notifications again from the current files"


@pytest.mark.parametrize("relative", ["tasks/main.yml", "defaults/main.yml", "handlers/main.yml"])
def test_e5_invalid_yaml_propagates(tmp_path: Path, relative: str) -> None:
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks/main.yml").write_text("[]", encoding="utf-8")
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("broken: [", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        role_problems(tmp_path)
