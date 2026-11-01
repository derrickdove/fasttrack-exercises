# d44 — Docker and Ansible: a test station as files

**Time:** about 57 minutes (27 graded + 30 live drill) · **Read first:** Docker [Get started](https://docs.docker.com/get-started/) and the [Dockerfile reference](https://docs.docker.com/reference/dockerfile/); Ansible [Getting started](https://docs.ansible.com/ansible/latest/getting_started/index.html), [Intro to playbooks](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html), and [Roles](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html) · **You edit:** `starter/Dockerfile`, `starter/playbook.yml`, and `starter/inventory.ini`; scratch files during the live drill

## What you're building

An operator needs the same chassis tester software on every bench computer. You will describe its Python environment and station setup in files, then run a small Ansible role against your own Linux account. The graded checks only read files; the separate live drill installs Ansible and writes a practice station configuration under your home folder. The Python inspection helpers are supplied in full. You need **WSL2** (Windows Subsystem for Linux, version 2), which runs Ubuntu Linux on Windows, for the drill; the graded exercises need neither Docker nor Ansible installed.

## How this works

1. E1–E3: replace the placeholder comments in the three deployment files. Leave the supplied `starter/deploycheck.py` as it is. Don't edit `tests/` or the empty `starter/__init__.py`.
2. Press **Ctrl+Shift+B → Test: d44** (or run `bash tools/run.sh d44` / `tools\run.ps1 d44`). At first you'll see `Exercises: 0 / 3 passed`. Comment-only deployment files deliberately report `NotImplementedError`; once filled in, they get structural assertions. Rerun after each exercise.
3. Complete the unscored live drill below, including cleanup. Report **all pass / partial / stuck** in the tracker; record the three observed change counts separately from the exercise score.

A **deployment** is putting software and configuration on a computer. A Docker **image** is a packaged filesystem and startup recipe; a **container** is a running instance of that image. A **Dockerfile** lists instructions for constructing an image. A **base image** supplies the starting filesystem; its **tag**, such as `3.12-slim`, selects a version and variant. **Root** is Linux's unrestricted administrator account; the station process should use another account.

**YAML** is a text format whose indentation expresses structure. A **mapping** pairs keys with values (a Python `dict` after loading); a **sequence** holds ordered items (a Python `list`). A **boolean** is true or false; write `true` and `false` without quotes in YAML. **PyYAML** is the installed Python library for reading YAML; `yaml.safe_load(text)` loads data without constructing arbitrary Python objects. An empty or comment-only document loads as `None`.

An Ansible **inventory** lists managed computers, called **hosts**, grouped by purpose. A host **alias** is the inventory name used for a computer. A **playbook** is a YAML document containing **plays**: each play selects hosts and lists **tasks** to run on them. A task calls a **module**, a named Ansible operation such as copying a file. `ansible.builtin.` identifies Ansible's built-in modules. A **role** bundles reusable tasks and related files; you will create a tiny role in the live drill.

For example, this diagnostic play loads as a list of play dictionaries:

```python
import yaml
text = "- hosts: diagnostics\n  tasks: []\n"
plays = yaml.safe_load(text)
print(plays[0]["hosts"])  # diagnostics
```

## Exercises

### E1 — Package the tester environment (easy, ~10 min)

**Goal:** Write `starter/Dockerfile` for the chassis tester. A **working directory** is the default folder for later instructions. `COPY` places files in the image, `RUN` executes a build step, `USER` selects the runtime account, and `CMD` or `ENTRYPOINT` sets the startup command.

**File contract** (no Python function):

- Use one build stage (one base image and its following instructions): the first instruction is `FROM python:3.12-slim`. Other Python 3.12 slim tags are accepted, including `python:3.12.8-slim-bookworm`.
- Set an absolute `WORKDIR`, such as `/station`, before copying. Use shell form (space-separated arguments): `COPY . .` or `COPY . /station` to copy the entire project into that directory. Trailing `/` characters on `WORKDIR` or the destination are accepted. The dot means the current project directory.
- Include `RUN pip install PACKAGE` or `RUN python -m pip install PACKAGE`. Here `PACKAGE` is a package name or path; `.` installs the copied project, so the project `COPY` must come before any installation from `.`. `python3` is also accepted.
- The effective startup command must invoke `python -m chassis`; optional arguments may follow. Docker uses the last `CMD` and last `ENTRYPOINT` written in this Dockerfile, regardless of their order. Setting `ENTRYPOINT` resets any `CMD` supplied by the base image. An argument-list `ENTRYPOINT` receives `CMD` as arguments, while a shell-form `ENTRYPOINT` ignores `CMD`. Use either a JSON argument list (brackets with quoted strings, like `["tool", "--help"]`) or shell form. `python3` is also accepted. `-m` runs the named Python module.
- The final `USER` must be a non-root username or nonzero numeric user ID. A `user:group` form is accepted. If you choose a username, include a build step to create that account; account creation isn't executed or checked here.

**Example:** `WORKDIR /station` makes `/station` the directory used by following instructions. This is one instruction, not the complete Dockerfile.

**Watch out:** Use one instruction per line, without continuation lines or inline comments. Full-line `#` comments and blank lines are allowed; instruction names are case insensitive. Use a single stage without build aliases. The hypothetical project supplies the `chassis` module and packaging metadata; this set does not supply a buildable project.

**Reread:** Docker Get started, “Docker concepts” (images and containers); Dockerfile reference, `FROM`, `WORKDIR`, `COPY`, `RUN`, `USER`, `CMD`, and `ENTRYPOINT`.

### E2 — Describe station setup (easy, ~12 min)

**Goal:** Write `starter/playbook.yml`. **Privilege escalation**, selected by `become: true`, lets setup perform administrator operations. A **service unit** is a file describing a background process to Linux's **systemd** service manager. A **virtual environment** is a folder with its own Python interpreter and installed packages. Ubuntu 24.04 marks system Python as externally managed under **PEP 668** (a Python packaging rule), so install the tester into a virtual environment instead of system Python.

**File contract** (no Python function): write a YAML list with exactly one play. It must have `hosts: test_stations`, `become: true`, and a nonempty `tasks` list. Every task has a nonempty string `name` and exactly one `ansible.builtin.*` module. Use separate tasks for the four operations:

- Install the unit using `ansible.builtin.copy` or `ansible.builtin.template`. Its parameter mapping needs a nonempty `src` (source filename) and `dest: /etc/systemd/system/chassis-telemetry.service`. A template is a source file whose variables Ansible fills in. The future unit must run the tester with `/opt/chassis/.venv/bin/python`, the interpreter in the virtual environment below.
- Before the pip task, install `python3-venv` using `ansible.builtin.apt`, Ubuntu's system-package module, with `name: python3-venv` (or a list containing that name) and `state: present`. This package supplies Python's virtual-environment creation support.
- Install the tester package using `ansible.builtin.pip` with a nonempty `name` (for example, `/opt/chassis`), `virtualenv: /opt/chassis/.venv`, and `virtualenv_command: python3 -m venv`. The `virtualenv` parameter selects the installation environment; `virtualenv_command` tells Ansible how to create it if it is missing.
- Manage the service using `ansible.builtin.systemd` or `ansible.builtin.systemd_service`. Set `name` to `chassis-telemetry` or `chassis-telemetry.service`, `enabled: true`, `state: started`, and `daemon_reload: true`. Enabled means start at boot; started means running now; daemon reload tells systemd to reread unit definitions.

**Example:** a task name such as `Install meter driver` describes an operation to the operator; the module key underneath selects the operation.

**Watch out:** Use spaces for YAML indentation. Quoted `"true"` is a string and fails the boolean checks. Source files and packages represent a future deployment; you don't need to create them. E2 checks the playbook's structure; it does not run Ansible or inspect the future unit's contents.

**Reread:** Ansible Getting started, “Creating a playbook”; Intro to playbooks, “Playbook syntax” and “Executing playbooks”; Roles, “Role directory structure” (context for grouping these files later).

### E3 — Group the bench computers (easy, ~5 min)

**Goal:** Write `starter/inventory.ini`, using Ansible's INI inventory format (text divided into named sections): `[group]` headers followed by one host alias per line, optionally followed by variables like `ansible_host=192.0.2.20`. `ansible_host` gives an address when the alias isn't a resolvable network name.

**File contract** (no Python function): define `bench` with at least one host. Define `test_stations` so it includes every bench host. Either repeat the bench host aliases in `[test_stations]`, or define `[test_stations:children]` with `bench` on the next line. A **child group** contributes all its hosts to its parent. No other child-group nesting is needed. Extra direct hosts are allowed.

**Example:** `[diagnostics]` followed by `diag01 ansible_host=192.0.2.20` defines a diagnostics group with one host. Use your required group names for this station set.

**Watch out:** Do not write the literal header `[test_stations:children]` followed by a host: it lists group names. Blank lines and full-line `#` or `;` comments are allowed. The tests read aliases and group membership; addresses never get contacted.

**Reread:** Ansible Getting started, “Building an inventory,” including host groups and parent/child groups.

## Supplied tools (complete; no learner edits)

These helpers inspect files without executing Ansible. They are ready to use; they do not count toward the three graded exercises.

### `idempotent_tasks` — find commands needing review (supplied)

**Goal:** Read a playbook with the supplied `idempotent_tasks` in `starter/deploycheck.py`. Despite the function name, its result lists tasks **missing** an idempotence guard (a condition that avoids repeating a change).

**Idempotence** means repeating an operation has the same effect as doing it once. Modules such as `copy` usually compare the current and desired state. Raw commands may repeat a change on every run, so station setup needs extra care:

- `creates: PATH` skips a command when that path already exists.
- `removes: PATH` skips a command when that path is absent.
- `changed_when` controls whether Ansible reports a task as changed. Use `changed_when: false` for a **read-only** check: a command that queries the station without changing it. This controls reporting and does not itself prevent side effects.

**Signature:** `def idempotent_tasks(playbook_path: str | Path) -> list[str]`

**Exact contract:**

1. Read the path as UTF-8 (a standard text encoding) and load it with `yaml.safe_load`. An empty/comment-only document, or `[]`, returns `[]`.
2. Otherwise the input is a list of play mappings. Inspect each play's direct `tasks` list, in document order. A missing `tasks` key means an empty list. Tasks are mappings with string `name` values. Each task has at most one action module.
3. Consider only `ansible.builtin.command` and `ansible.builtin.shell`. Their value is either a command string or a parameter mapping with `cmd`. Ignore other modules. Only these fully qualified names are in scope.
4. A considered task is guarded if `creates` or `removes` is present in the module's parameter mapping or the task's `args` mapping, **or** task-level `changed_when` loads as the boolean `False` (YAML `false`). For `creates`/`removes`, check key presence, not the path's value. Missing `args` means an empty mapping. Other `changed_when` values, including `true`, condition expressions, `[]`, quoted `"false"`, `0`, and `null` (YAML's empty value, loaded as Python `None`), do not guard a task; without a file guard, keep it on the review list.
5. Return unguarded task names in play/task order. Preserve duplicate names. Don't inherit guards from another task or the play. `register` stores a result, `when` decides whether a task runs, and `chdir` selects a directory; none counts as a guard here.
6. Let file-reading errors (`OSError`, including `FileNotFoundError`) and invalid YAML errors (`yaml.YAMLError`) propagate to the caller. You don't need to validate other document shapes or evaluate commands, paths, or conditions.

**Example:** a task named `Read serial number` using `ansible.builtin.command: station-id` with no guard returns `["Read serial number"]` when it is the only task. Add task-level `changed_when: false` and the result is `[]`. A task named `Initialize station` using `ansible.builtin.command: station-init` with `changed_when: true` returns `["Initialize station"]`; adding `args: {creates: /opt/chassis/ready}` makes the result `[]`.

**Watch out:** This is a small review rule, not a proof that a deployment is idempotent. Use `changed_when: false` only for read-only checks; it does not make a mutating command safe to repeat. The checker does not determine what a command does. Inputs use direct tasks only: no roles, nested task blocks, handlers (tasks triggered by changes), task includes, short module aliases, or inline `creates=...`/`removes=...` inside command strings. All guarded paths use explicit YAML keys. This helper can inspect a separate practice file before E2 is finished.

**Reread:** Ansible Intro to playbooks, “Desired state and idempotency”; Getting started, “Creating a playbook.”

### `role_problems` — check an Ansible role layout (supplied)

**Goal:** Use the supplied `role_problems` in `starter/deploycheck.py` to check the folders in `data/roles/` before a role reaches a bench computer. This helper only reads files; the live drill below runs Ansible.

A **variable** is a named setting. A role's `tasks/main.yml` is its starting task list. `defaults/main.yml` holds default variable values (settings that callers may replace). `handlers/main.yml` lists named handlers, such as a service restart. A task's **notification**, written as `notify`, names a handler to trigger when that task changes something. This check only matches the names in the files; it does not predict whether a task will change anything.

**Signature:** `def role_problems(role_dir: Path) -> list[str]`

**Exact contract:**

1. `role_dir` is a `pathlib.Path` pointing to an existing role folder. Report `"tasks/main.yml: missing"` when that file is absent, but keep checking the other files. `defaults/main.yml` and `handlers/main.yml` are optional; their absence alone is fine.
2. Read each inspected file as UTF-8 and load it with `yaml.safe_load`. If `defaults/main.yml` is present but does not load as a mapping (`dict`), report `"defaults/main.yml: expected a mapping"`. An empty mapping (`{}`) is valid; an empty/comment-only file loads as `None` and is invalid.
3. Inspect every file directly inside `tasks/` whose extension is `.yml`, including `main.yml`. Ignore nested folders, other extensions, and all other role files. Each task file must load as a list; otherwise report `"tasks/<file>.yml: expected a list"` and skip its tasks. An empty list (`[]`) is valid; an empty/comment-only file is invalid.
4. Items in each task list are mappings. Count tasks starting at 1 separately in each file. A task needs a nonempty string `name`; a missing key, `null`, a non-string, or a string containing only whitespace (spaces, tabs, or newlines) counts as no name. Report `"tasks/<file>.yml: task <number> has no name"`. Continue checking that task's notifications too.
5. When present, `handlers/main.yml` is a list of mappings with unique, nonempty string `name` values; you may assume that shape. `[]` is allowed. A task's `notify` is either one handler-name string or a list of such strings; a missing `notify` means no notifications. You may assume those shapes too. Match handler names exactly, including case and spaces, across all inspected task files.
6. For each task, report each distinct missing handler once as `"tasks/<file>.yml: task <number> notifies unknown handler '<name>'"`. If two tasks notify the same missing handler, report it once for each task. For each defined handler that no inspected task notifies, report `"handlers/main.yml: handler '<name>' is never notified"`. Duplicate notifications within one task cause no extra messages. A notification in a task without a name still counts.
7. Return all messages in ascending string order, using `sorted`. Use `/` in message paths on Windows and Linux, never include `role_dir` itself, and replace the angle-bracket placeholders above with the actual filename, number, or handler name. No problems means `[]`.
8. Let file-reading errors (`OSError`) and invalid YAML errors (`yaml.YAMLError`) propagate. You do not need to validate other input shapes. There are no nested task blocks, task includes (instructions to load another task file), or handler aliases (`listen`, an alternative notification name). Do not follow references or evaluate modules.

**Example:** with your working directory set to `sets/d44/`, using the supplied role folders:

```python
from pathlib import Path
from starter.deploycheck import role_problems
roles = Path("data/roles")
role_problems(roles / "good")
# []
role_problems(roles / "notify_mismatch")
# ["handlers/main.yml: handler 'Restart station' is never notified",
#  'tasks/main.yml: task 1 has no name',
#  "tasks/main.yml: task 2 notifies unknown handler 'Reload driver'"]
```

**Watch out:** Task and handler names serve different purposes: a task's `notify` must match a handler's `name`, not another task's name. Use `isinstance(value, dict)` or `isinstance(value, list)` to check the loaded document shape before iterating. Missing `tasks/main.yml` is a problem even if other task files exist. Use fresh collections on each call.

**Reread:** Ansible Roles, “Role directory structure”; Intro to playbooks, “Handlers: running operations on change” (linked from that guide).

## Live drill (WSL2 Ubuntu, ~30 min)

This drill is **unscored**: pytest does not execute it. Open the WSL2 Ubuntu terminal and keep using that terminal through cleanup. An Ubuntu-based **Codespace** (a hosted Linux development environment) with `sudo` and package-install access can also run this drill; it needs no systemd service. If those are unavailable, use WSL2 Ubuntu. Do not run E2's station playbook: this drill uses its own scratch files (temporary practice files).

An operation is **idempotent** when applying the same desired state again changes nothing. Ansible's **PLAY RECAP** is the final per-host summary: `ok` counts successful tasks, including successful tasks that changed something; `changed` counts tasks that changed the host; `unreachable` counts connection failures; `failed` counts task failures. Read these together: `changed=0` alone does not prove success.

### Install the tool and prepare scratch folders (~8 min)

Run these in Ubuntu. `sudo` runs a command with administrator permission; `apt` manages Ubuntu packages. `update` refreshes the available-package list; `install -y` installs without a confirmation prompt. Only tool installation needs administrator permission.

```bash
sudo apt update
sudo apt install -y ansible
ansible-playbook --version
mkdir "$HOME/ansible-lab"
```

`$HOME` is your home folder; `~/ansible-lab/` means the same location as `$HOME/ansible-lab/`. If any command fails, stop and resolve it before continuing. In particular, if `mkdir` reports that `ansible-lab` already exists, preserve it and use a clean practice account for this drill. Cleanup below assumes this drill created that folder.

`mktemp -d` creates a uniquely named scratch directory; `lab_source` stores its path. `mkdir -p` creates the role's nested folders. `cd` changes your terminal's working directory.

```bash
lab_source=$(mktemp -d "$HOME/fasttrack-d44.XXXXXX")
cd "$lab_source"
mkdir -p roles/station/tasks roles/station/defaults roles/station/templates
```

### Write one tiny role (~10 min)

This role's default `station_name` will fill the template. The `.j2` extension marks a **Jinja template**, text where `{{ variable_name }}` is replaced with that variable's value. `cat > FILE <<'YAML'` writes the following lines to FILE until a line containing only `YAML`; the quoted delimiter keeps the shell from expanding the text. Copy each complete command block, including its closing delimiter.

```bash
cat > roles/station/defaults/main.yml <<'YAML'
station_name: bench-a
YAML

cat > roles/station/templates/station.conf.j2 <<'TEMPLATE'
station_name={{ station_name }}
TEMPLATE

cat > roles/station/tasks/main.yml <<'YAML'
- name: Install practice station configuration
  ansible.builtin.template:
    src: station.conf.j2
    dest: "{{ lookup('ansible.builtin.env', 'HOME') }}/ansible-lab/station.conf"
    mode: '0644'
YAML

cat > playbook.yml <<'YAML'
- name: Configure a practice station
  hosts: localhost
  connection: local
  become: false
  gather_facts: false
  roles:
    - station
YAML
```

`tasks/main.yml` is the role's starting task list; Ansible finds `station` under the adjacent `roles/` folder. The template's `src` is relative to the role's `templates/` folder. `lookup('ansible.builtin.env', 'HOME')` reads your terminal's home-directory environment variable. `mode: '0644'` gives the owner read/write permission and others read permission.

`localhost` is this computer; `connection: local` runs tasks directly here without a remote connection. `become: false` keeps tasks under your account. **Facts** are host details Ansible can collect automatically; `gather_facts: false` disables that extra task so the recap covers just the template task. The destination folder already exists because you created it above.

### Apply twice, then change a variable (~9 min)

Run these commands from the scratch directory. `-i` selects an inventory; the trailing comma in `'localhost,'` makes it an inline host list rather than a filename. `cat` prints the installed file.

```bash
ansible-playbook -i 'localhost,' playbook.yml
cat "$HOME/ansible-lab/station.conf"
ansible-playbook -i 'localhost,' playbook.yml
```

On the first run, the file did not exist: find `changed=1` in the `localhost` PLAY RECAP and `station_name=bench-a` in the installed file. On the second run, the desired file already matches: find `changed=0`. Both recaps must show `ok=1`, `unreachable=0`, and `failed=0`. You have observed idempotence: running the same role again changes nothing.

Now edit the variable used by the template by replacing the defaults file:

```bash
cat > roles/station/defaults/main.yml <<'YAML'
station_name: bench-b
YAML
ansible-playbook -i 'localhost,' playbook.yml
cat "$HOME/ansible-lab/station.conf"
```

This recap should show `ok=1`, `changed=1`, `unreachable=0`, and `failed=0`; the installed file should now contain `station_name=bench-b`. The desired configuration changed, so Ansible updated the file. Record the three `changed` counts (1, 0, 1) and explain why each occurred. If they differ, inspect the task output and installed file before repeating; do not hide a change with `changed_when: false`.

### Clean up (~3 min)

Always remove this drill's files when finished, including after an unexpected observation. `rm` removes the named files; `rmdir` removes only empty directories, so additional files are preserved. Run from the scratch directory; these commands leave Ansible installed for later practice.

```bash
rm -- "$HOME/ansible-lab/station.conf"
rmdir -- "$HOME/ansible-lab"
rm -- playbook.yml roles/station/defaults/main.yml roles/station/tasks/main.yml roles/station/templates/station.conf.j2
rmdir -- roles/station/defaults roles/station/tasks roles/station/templates roles/station roles
cd "$HOME"
rmdir -- "$lab_source"
```

If a file was never created, its removal may report that it is missing; continue removing the other listed files. Confirm that the output folder and scratch directory are gone:

```bash
test ! -e "$HOME/ansible-lab" && echo "Output folder removed"
test ! -e "$lab_source" && echo "Role scratch folder removed"
```

`test ! -e` succeeds when a path does not exist; `&&` runs the following command only on success. Both confirmation messages should appear.
