# d38 — Docker and Ansible: a test station as files

**Time:** about 57 minutes · **Read first:** Docker [Get started](https://docs.docker.com/get-started/) and the [Dockerfile reference](https://docs.docker.com/reference/dockerfile/); Ansible [Getting started](https://docs.ansible.com/ansible/latest/getting_started/index.html), [Intro to playbooks](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html), and [Roles](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html) · **You edit:** `starter/Dockerfile`, `starter/playbook.yml`, `starter/inventory.ini`, and `starter/deploycheck.py`

## What you're building

An operator needs the same chassis tester software on every bench computer. You will describe its Python environment and station setup in files, then write a Python check that spots commands which may change the station every time setup runs. These are structural checks: they read files, never build an image, install software, or contact a station. Docker, Ansible, Linux, and a running chassis application are not needed for this set.

## How this works

1. E1–E3: replace the placeholder comments in the three deployment files. E4: replace `raise NotImplementedError(...)` in `starter/deploycheck.py`. Don't edit `tests/` or the empty `starter/__init__.py`.
2. Press **Ctrl+Shift+B → Test: d38** (or run `bash tools/run.sh d38` / `tools\run.ps1 d38`). At first you'll see `Exercises: 0 / 5 passed`. Comment-only deployment files deliberately report `NotImplementedError`; once filled in, they get structural assertions. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **deployment** is putting software and configuration on a computer. A Docker **image** is a packaged filesystem and startup recipe; a **container** is a running instance of that image. A **Dockerfile** lists instructions for constructing an image. A **base image** supplies the starting filesystem; its **tag**, such as `3.12-slim`, selects a version and variant. **Root** is Linux's unrestricted administrator account; the station process should use another account.

An Ansible **inventory** lists managed computers, called **hosts**, grouped by purpose. A host **alias** is the inventory name used for a computer. A **playbook** is a YAML document containing **plays**: each play selects hosts and lists **tasks** to run on them. A task calls a **module**, a named Ansible operation such as copying a file. `ansible.builtin.` identifies Ansible's built-in modules. A **role** bundles reusable tasks and related files; roles are reading context today, and you won't create one here.

**YAML** is a text format whose indentation expresses structure. A **mapping** pairs keys with values (a Python `dict` after loading); a **sequence** holds ordered items (a Python `list`). A **boolean** is true or false; write `true` and `false` without quotes in YAML. **PyYAML** is the installed Python library for reading YAML; `yaml.safe_load(text)` loads data without constructing arbitrary Python objects. An empty or comment-only document loads as `None`.

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
- The effective startup command must invoke `python -m chassis`; optional arguments may follow. Docker uses the last `CMD` and last `ENTRYPOINT`; setting `ENTRYPOINT` clears an earlier `CMD`. An argument-list `ENTRYPOINT` receives `CMD` as arguments, while a shell-form `ENTRYPOINT` ignores `CMD`. Use either a JSON argument list (brackets with quoted strings, like `["tool", "--help"]`) or shell form. `python3` is also accepted. `-m` runs the named Python module.
- The final `USER` must be a non-root username or nonzero numeric user ID. A `user:group` form is accepted. If you choose a username, include a build step to create that account; account creation isn't executed or checked here.

**Example:** `WORKDIR /station` makes `/station` the directory used by following instructions. This is one instruction, not the complete Dockerfile.

**Watch out:** Use one instruction per line, without continuation lines or inline comments. Full-line `#` comments and blank lines are allowed; instruction names are case insensitive. Use a single stage without build aliases. The hypothetical project supplies the `chassis` module and packaging metadata; this set does not supply a buildable project.

**Reread:** Docker Get started, “Docker concepts” (images and containers); Dockerfile reference, `FROM`, `WORKDIR`, `COPY`, `RUN`, `USER`, `CMD`, and `ENTRYPOINT`.

### E2 — Describe station setup (easy, ~12 min)

**Goal:** Write `starter/playbook.yml`. **Privilege escalation**, selected by `become: true`, lets setup perform administrator operations. A **service unit** is a file describing a background process to Linux's **systemd** service manager.

**File contract** (no Python function): write a YAML list with exactly one play. It must have `hosts: test_stations`, `become: true`, and a nonempty `tasks` list. Every task has a nonempty string `name` and exactly one `ansible.builtin.*` module. Use separate tasks for the three operations:

- Install the unit using `ansible.builtin.copy` or `ansible.builtin.template`. Its parameter mapping needs a nonempty `src` (source filename) and `dest: /etc/systemd/system/chassis-telemetry.service`. A template is a source file whose variables Ansible fills in.
- Install the tester package using `ansible.builtin.pip` with a nonempty `name`, or `ansible.builtin.command` with a nonempty command string (or mapping with `cmd`). Prefer `pip` for this exercise. The check only verifies this structure, not what a command installs.
- Manage the service using `ansible.builtin.systemd` or `ansible.builtin.systemd_service`. Set `name` to `chassis-telemetry` or `chassis-telemetry.service`, `enabled: true`, `state: started`, and `daemon_reload: true`. Enabled means start at boot; started means running now; daemon reload tells systemd to reread unit definitions.

**Example:** a task name such as `Install meter driver` describes an operation to the operator; the module key underneath selects the operation.

**Watch out:** Use spaces for YAML indentation. Quoted `"true"` is a string and fails the boolean checks. Source files and packages represent a future deployment; you don't need to create them. E2 checks structure separately from E4, so a command installation task can pass E2 even when E4 would flag it.

**Reread:** Ansible Getting started, “Creating a playbook”; Intro to playbooks, “Playbook syntax” and “Executing playbooks”; Roles, “Role directory structure” (context for grouping these files later).

### E3 — Group the bench computers (easy, ~5 min)

**Goal:** Write `starter/inventory.ini`, using Ansible's INI inventory format (text divided into named sections): `[group]` headers followed by one host alias per line, optionally followed by variables like `ansible_host=192.0.2.20`. `ansible_host` gives an address when the alias isn't a resolvable network name.

**File contract** (no Python function): define `bench` with at least one host. Define `test_stations` so it includes every bench host. Either repeat the bench host aliases in `[test_stations]`, or define `[test_stations:children]` with `bench` on the next line. A **child group** contributes all its hosts to its parent. No other child-group nesting is needed. Extra direct hosts are allowed.

**Example:** `[diagnostics]` followed by `diag01 ansible_host=192.0.2.20` defines a diagnostics group with one host. Use your required group names for this station set.

**Watch out:** Do not write the literal header `[test_stations:children]` followed by a host: it lists group names. Blank lines and full-line `#` or `;` comments are allowed. The tests read aliases and group membership; addresses never get contacted.

**Reread:** Ansible Getting started, “Building an inventory,” including host groups and parent/child groups.

### E4 — Find commands needing review (medium, ~18 min)

**Goal:** Implement `idempotent_tasks` in `starter/deploycheck.py`. Despite the supplied function name, its result lists tasks **missing** an idempotence guard.

**Idempotence** means repeating an operation has the same effect as doing it once. Modules such as `copy` usually compare the current and desired state. Raw commands may repeat a change on every run, so station setup needs extra care:

- `creates: PATH` skips a command when that path already exists.
- `removes: PATH` skips a command when that path is absent.
- `changed_when` controls whether Ansible reports a task as changed; `changed_when: false` is useful for a read-only instrument query. This controls reporting and does not itself prevent side effects.

**Signature:** `def idempotent_tasks(playbook_path: str | Path) -> list[str]`

**Exact contract:**

1. Read the path as UTF-8 (a standard text encoding) and load it with `yaml.safe_load`. An empty/comment-only document, or `[]`, returns `[]`.
2. Otherwise the input is a list of play mappings. Inspect each play's direct `tasks` list, in document order. A missing `tasks` key means an empty list. Tasks are mappings with string `name` values. Each task has at most one action module.
3. Consider only `ansible.builtin.command` and `ansible.builtin.shell`. Their value is either a command string or a parameter mapping with `cmd`. Ignore other modules. Only these fully qualified names are in scope.
4. A considered task is guarded if **any** of these keys is present: `creates` or `removes` in the module's parameter mapping, `creates` or `removes` in the task's `args` mapping, or `changed_when` at task level. Check key presence, not truthiness: `changed_when: false` still counts. Missing `args` means an empty mapping.
5. Return unguarded task names in play/task order. Preserve duplicate names. Don't inherit guards from another task or the play. `register` stores a result, `when` decides whether a task runs, and `chdir` selects a directory; none counts as a guard here.
6. Let file-reading errors (`OSError`, including `FileNotFoundError`) and invalid YAML errors (`yaml.YAMLError`) propagate to the caller. You don't need to validate other document shapes or evaluate commands, paths, or conditions.

**Example:** a task named `Read serial number` using `ansible.builtin.command: station-id` with no guard contributes `"Read serial number"`. Add task-level `changed_when: false` and it contributes nothing.

**Watch out:** This is a small review rule, not a proof that a deployment is idempotent. It accepts any present `changed_when` value, even `true`. Inputs use direct tasks only: no roles, nested task blocks, handlers (tasks triggered by changes), task includes, short module aliases, or inline `creates=...`/`removes=...` inside command strings. All guarded paths use explicit YAML keys. Tests use temporary playbooks, so E4 can pass before E2 is finished.

**Reread:** Ansible Intro to playbooks, “Desired state and idempotency”; Getting started, “Creating a playbook.”

### E5 — Check an Ansible role layout (easy–medium, ~12 min)

**Goal:** Implement `role_problems` in `starter/deploycheck.py` by replacing its `raise NotImplementedError(...)` line. The team groups station setup into reusable roles. Check the supplied folders in `data/roles/` before a role reaches a bench computer. You only read files; you never run Ansible.

A role's `tasks/main.yml` is its starting task list. `defaults/main.yml` holds default variable values (settings that callers may replace). `handlers/main.yml` lists named handlers, such as a service restart. A task's **notification**, written as `notify`, names a handler to trigger when that task changes something. This check only matches the names in the files; it does not predict whether a task will change anything.

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

**Example:** with your working directory set to `sets/d38/`, using the supplied role folders:

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
