"""Supplied inspection helpers: complete; no learner edits needed.

These read deployment files without running Docker or Ansible.
"""
from pathlib import Path

import yaml  # type: ignore[import-untyped]


def idempotent_tasks(playbook_path: str | Path) -> list[str]:
    """Return names of unguarded command/shell tasks in document order."""
    plays = yaml.safe_load(Path(playbook_path).read_text(encoding="utf-8")) or []
    unguarded: list[str] = []
    for play in plays:
        for task in play.get("tasks", []):
            for module in ("ansible.builtin.command", "ansible.builtin.shell"):
                if module not in task:
                    continue
                parameters = task[module]
                module_args = parameters if isinstance(parameters, dict) else {}
                args = task.get("args", {})
                guarded = task.get("changed_when") is False or any(
                    key in module_args or key in args for key in ("creates", "removes")
                )
                if not guarded:
                    unguarded.append(task["name"])
    return unguarded


def role_problems(role_dir: Path) -> list[str]:
    """Return sorted layout, task-name, and notification problems for a role."""
    problems: list[str] = []
    if not (role_dir / "tasks/main.yml").is_file():
        problems.append("tasks/main.yml: missing")

    defaults_path = role_dir / "defaults/main.yml"
    if defaults_path.is_file():
        defaults = yaml.safe_load(defaults_path.read_text(encoding="utf-8"))
        if not isinstance(defaults, dict):
            problems.append("defaults/main.yml: expected a mapping")

    handler_names: set[str] = set()
    handlers_path = role_dir / "handlers/main.yml"
    if handlers_path.is_file():
        handlers = yaml.safe_load(handlers_path.read_text(encoding="utf-8"))
        handler_names = {handler["name"] for handler in handlers}

    notified: set[str] = set()
    for task_path in sorted((role_dir / "tasks").glob("*.yml")):
        if not task_path.is_file():
            continue
        relative = task_path.relative_to(role_dir).as_posix()
        tasks = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        if not isinstance(tasks, list):
            problems.append(f"{relative}: expected a list")
            continue
        for number, task in enumerate(tasks, start=1):
            name = task.get("name")
            if not isinstance(name, str) or not name.strip():
                problems.append(f"{relative}: task {number} has no name")
            notifications = task.get("notify", [])
            if isinstance(notifications, str):
                notifications = [notifications]
            for handler_name in set(notifications):
                notified.add(handler_name)
                if handler_name not in handler_names:
                    problems.append(
                        f"{relative}: task {number} notifies unknown handler '{handler_name}'"
                    )

    for handler_name in handler_names - notified:
        problems.append(f"handlers/main.yml: handler '{handler_name}' is never notified")
    return sorted(problems)
