"""Show first-pass times and estimated exercise minutes from the local run log."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import re


def exercise_ids(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or re.fullmatch(r"E[0-9]+", item) is None:
            return None
        result.append(item)
    return result


def read_runs(path: Path, identifier: str) -> list[tuple[datetime, list[str], list[str]]]:
    runs: list[tuple[datetime, list[str], list[str]]] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as log:
            for line in log:
                try:
                    entry = json.loads(line)
                    if not isinstance(entry, dict) or entry.get("set") != identifier:
                        continue
                    stamp = entry.get("time")
                    total = entry.get("total")
                    passed = exercise_ids(entry.get("passed"))
                    failed = exercise_ids(entry.get("failed"))
                    if (not isinstance(stamp, str) or type(total) is not int or total <= 0
                            or passed is None or failed is None):
                        continue
                    if len(set(passed + failed)) != total or len(passed + failed) != total:
                        continue
                    time = datetime.fromisoformat(stamp)
                    if time.utcoffset() is None:
                        continue
                    runs.append((time, passed, failed))
                except (ValueError, TypeError):
                    continue
    except OSError:
        pass
    return sorted(runs, key=lambda run: run[0])


def report(path: Path, identifier: str, break_minutes: float = 20) -> str:
    runs = read_runs(path, identifier)
    if not runs:
        return f"No data for {identifier}."
    previous = runs[0][0]
    first_pass: dict[str, tuple[datetime, str]] = {}
    exercises: set[str] = set()
    active = timedelta()
    pending = timedelta()
    breaks = timedelta()

    def display(duration: timedelta) -> str:
        minutes = duration.total_seconds() / 60
        return f"{minutes:.0f}" if minutes.is_integer() else f"{minutes:.1f}"

    for time, passed, failed in runs:
        gap = time - previous
        previous = time
        if gap.total_seconds() / 60 <= break_minutes:
            active += gap
            pending += gap
        else:
            breaks += gap
        exercises.update(passed + failed)
        new_passes = sorted((name for name in passed if name not in first_pass),
                            key=lambda name: int(name[1:]))
        if new_passes:
            elapsed = f"{display(pending)} min"
            if breaks:
                elapsed += f" (plus a break of {display(breaks)} min)"
            first_pass[new_passes[0]] = (time, elapsed)
            for exercise in new_passes[1:]:
                first_pass[exercise] = (time, f"passed in the same run as {new_passes[0]}")
            pending = timedelta()
            breaks = timedelta()
    lines = [f"{identifier}: first run {runs[0][0].isoformat(timespec='seconds')}"]
    for exercise in sorted(exercises, key=lambda name: int(name[1:])):
        if exercise not in first_pass:
            lines.append(f"{exercise}: not yet")
            continue
        time, elapsed = first_pass[exercise]
        lines.append(f"{exercise}: {time.isoformat(timespec='seconds')} | {elapsed}")
    if first_pass and pending:
        lines.append(f"Still working: {display(pending)} min since the last new pass")
    lines.extend([f"Runs: {len(runs)}", f"Total active: {display(active)} min"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("set", help="Set id, for example p01.")
    parser.add_argument("--break-minutes", type=float, default=20)
    parser.add_argument("--file", type=Path, default=Path(__file__).resolve().parents[1] / ".ft-progress.jsonl")
    args = parser.parse_args()
    print(report(args.file, args.set, args.break_minutes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
