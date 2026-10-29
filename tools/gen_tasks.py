"""Regenerate build tasks after adding sets or gates. Run from any directory."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def set_order(identifier: str) -> tuple[int, int, str]:
    """Days use (day, 0); rN follows d(7*N-1); checkN follows dN and reviews.

    For example: d06, r1, d07; d30, check30, d31; d41, r6, d42.
    Unknown folder names sort last, alphabetically.
    """
    day = re.fullmatch(r"d(\d+)(?:-.*)?", identifier)
    review = re.fullmatch(r"r(\d+)", identifier)
    check = re.fullmatch(r"check(\d+)", identifier)
    if day:
        return int(day[1]), 0, identifier
    if review:
        return 7 * int(review[1]) - 1, 1, identifier
    if check:
        return int(check[1]), 2, identifier
    return 10000, 0, identifier


def task(identifier: str, gate: bool = False) -> dict:
    return {
        "label": f"{'Gate' if gate else 'Test'}: {identifier}",
        "type": "shell", "command": "bash",
        "args": ["${workspaceFolder}/tools/run.sh", identifier],
        "windows": {
            "command": "powershell",
            "args": ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                     "${workspaceFolder}\\tools\\run.ps1", identifier],
        },
        "group": "build", "problemMatcher": [],
        "presentation": {"reveal": "always", "panel": "dedicated", "clear": True},
    }


def main() -> None:
    sets = sorted((path.name for path in (ROOT / "sets").iterdir() if path.is_dir()), key=set_order)
    gates = sorted(path.name for path in (ROOT / "gates").glob("b[1-6]") if path.is_dir())
    tasks = [task(identifier) for identifier in sets] + [task(identifier, gate=True) for identifier in gates]
    destination = ROOT / ".vscode" / "tasks.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps({"version": "2.0.0", "tasks": tasks}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(tasks)} tasks to .vscode/tasks.json")


if __name__ == "__main__":
    main()
