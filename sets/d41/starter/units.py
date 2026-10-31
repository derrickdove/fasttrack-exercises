"""Read and check deployment files without starting a Linux service."""
from pathlib import Path
import tomllib
from typing import Any


# Supplied scaffolding: these two helpers are complete; do not edit them.
def parse_unit(path: str | Path) -> dict[str, dict[str, list[str]]]:
    """Read the documented unit subset, preserving repeated assignments in order."""
    # ponytail: single-line subset only; use systemd tooling for full unit syntax.
    parsed: dict[str, dict[str, list[str]]] = {}
    section: dict[str, list[str]] | None = None
    with Path(path).open(encoding="utf-8") as source:
        for number, raw_line in enumerate(source, 1):
            line = raw_line.strip()
            if not line or line.startswith(("#", ";")):
                continue
            if line.startswith("[") and line.endswith("]"):
                name = line[1:-1].strip()
                if not name:
                    raise ValueError(f"line {number}: empty section")
                section = parsed.setdefault(name, {})
                continue
            if section is None or "=" not in line:
                raise ValueError(f"line {number}: expected a section and key=value")
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                raise ValueError(f"line {number}: empty key")
            section.setdefault(key, []).append(value.strip())
    return parsed


def validate_unit(parsed: dict[str, dict[str, list[str]]]) -> list[str]:
    """Return the ordered station service checklist problems from README.md."""
    problems: list[str] = []
    unit = parsed.get("Unit", {})
    service = parsed.get("Service", {})
    install = parsed.get("Install", {})

    def last(section: dict[str, list[str]], key: str) -> str:
        values = section.get(key, [])
        return values[-1].strip() if values else ""

    if not last(unit, "Description"):
        problems.append("Description missing")
    for key in ("After", "Wants"):
        tokens = " ".join(unit.get(key, [])).split()
        if "network-online.target" not in tokens:
            problems.append(f"{key} must include network-online.target")
    if last(service, "Type") != "simple":
        problems.append("Type must be simple")
    command = last(service, "ExecStart").split()
    if (len(command) < 3 or not command[0].startswith("/")
            or command[0].rsplit("/", 1)[-1] not in ("python", "python3")
            or command[1:3] != ["-m", "chassis"]):
        problems.append("ExecStart must run an absolute python -m chassis command")
    restart = last(service, "Restart")
    if not restart:
        problems.append("Restart missing")
    elif restart != "on-failure":
        problems.append("Restart must be on-failure")
    delay = last(service, "RestartSec")
    if not delay:
        problems.append("RestartSec missing")
    else:
        try:
            seconds = int(delay)
        except ValueError:
            seconds = 0
        if seconds <= 0:
            problems.append("RestartSec must be positive whole seconds")
    user = last(service, "User")
    if not user:
        problems.append("User missing")
    elif user in ("root", "0"):
        problems.append("User is root")
    if "multi-user.target" not in " ".join(install.get("WantedBy", [])).split():
        problems.append("WantedBy must include multi-user.target")
    return problems


# Learner work starts here.
def diagnose_service() -> dict[str, dict[str, str]]:
    """Return your cause and fix for each case ID in the saved recordings."""
    raise NotImplementedError("E2: Read each recording and return its cause and fix by case ID")


def load_station_toml(path: str | Path) -> dict[str, Any]:
    """Load TOML and validate station.name and the instrument table list."""
    raise NotImplementedError("E3: Load TOML and name the first missing or mistyped key")
