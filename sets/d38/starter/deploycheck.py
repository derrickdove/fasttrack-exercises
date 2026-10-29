"""Review station deployment files without running Docker or Ansible."""
from pathlib import Path


def idempotent_tasks(playbook_path: str | Path) -> list[str]:
    """Return names of unguarded command/shell tasks in document order."""
    raise NotImplementedError("E4: Find command/shell tasks without an idempotence guard")