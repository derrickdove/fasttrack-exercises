"""Review station deployment files without running Docker or Ansible."""
from pathlib import Path

import yaml


def idempotent_tasks(playbook_path: str | Path) -> list[str]:
    """Return names of unguarded command/shell tasks in document order."""
    raise NotImplementedError("E4: Find command/shell tasks without an idempotence guard")


def role_problems(role_dir: Path) -> list[str]:
    """Return sorted layout, task-name, and notification problems for a role."""
    raise NotImplementedError("E5: Check role files and match task notifications to handlers")
