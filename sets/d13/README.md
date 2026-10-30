# d13 — Logging and structured reports

**Time:** about 45 minutes · **Read first:** [Python Logging HOWTO, Basic Logging Tutorial](https://docs.python.org/3/howto/logging.html#basic-logging-tutorial); Pro Git [3.5 Remote Branches](https://git-scm.com/book/en/v2/Git-Branching-Remote-Branches) and [3.6 Rebasing](https://git-scm.com/book/en/v2/Git-Branching-Rebasing); Python [`collections`: Counter and defaultdict](https://docs.python.org/3/library/collections.html) · **You edit:** `starter/reporting.py`

## What you're building

A test station runs checks on instrument channels (named measurement inputs, such as `CH1`). Operators need a readable event log and a machine-readable report to find failed checks and decide whether a run passed. You will build both from recorded check results; no instrument or network connection is needed.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/reporting.py`. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: d13** (or run `bash tools/run.sh d13` / `tools\run.ps1 d13` from the repo root). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

**UTF-8** is a text encoding that supports non-English characters. In type hints, `Any` means a value of any Python type; `Path` is a filesystem path object from `pathlib`.

A **logger** receives named events; a **handler** sends them somewhere, such as a file; a **formatter** controls their text. A **level** describes importance: DEBUG < INFO < WARNING < ERROR < CRITICAL. A logger's **propagation** setting controls whether parent loggers also receive its events.

A **status** is a check's outcome: `PASS` means within requirements, `FAIL` means outside requirements, and `ERROR` means the check could not finish. A **Counter** counts repeated values. A **defaultdict** supplies a new default value for a missing key, such as an empty list for a channel. Convert either to an ordinary `dict` when returning results.

```python
from collections import Counter, defaultdict
visits = Counter(["CH2", "CH2", "CH4"])
notes = defaultdict(list)
notes["CH4"].append("connector reseated")
print(visits["CH2"], notes["CH4"])  # 2 ['connector reseated']
```

**JSON** is a text format for dictionaries, lists, strings, numbers, booleans and null. **Metadata** describes the run, such as station and operator names. **UTC** is the shared world time reference. An **aware datetime** includes a time-zone offset; ISO 8601 is a standard timestamp spelling, such as `2026-10-28T12:30:00+00:00`. An **injectable time** lets tests supply a fixed datetime instead of reading the clock.

For E2–E4, every input result is a dictionary containing string keys `channel`, `status`, and `message`; all three values are strings. Status is always exactly `PASS`, `FAIL`, or `ERROR`. Other JSON-compatible fields may be present and must be preserved in reports. Inputs are valid; you do not need to validate malformed results. Do not change input dictionaries or lists. File paths accept `str` or `pathlib.Path`; parent directories already exist. Let file errors reach the caller.

## Exercises

### E1 — Station event log (easy, ~12 min)

**Goal:** Return the named `logging.Logger`, configured to append UTF-8 text to the supplied file. Set both logger and file handler to INFO, and set `propagate = False`. Use this exact formatter string: `"%(asctime)s %(levelname)s %(name)s: %(message)s"`, with logging's default timestamp format. Each accepted event occupies one line for the single-line messages used here.

**Signature:** `def get_station_logger(name: str, path: str | Path) -> logging.Logger`

**Example:** After `log = get_station_logger("station.chassis", "run.log")`, `log.info("power enabled")` adds a line ending `INFO station.chassis: power enabled`.

**Watch out:** DEBUG events must be omitted; INFO through CRITICAL must be recorded. Repeating a call with the same name and same path returns the same logger with exactly one file handler, so each event appears once. Existing file text stays intact. Different names use independent files. Names are fresh on first call; reconfiguring a name for a different path or handling externally installed handlers is outside this exercise. The caller owns closing the returned logger's handlers when finished; do not close them inside the function. No root logger configuration is needed.

**Reread:** Logging HOWTO → “Logging to a file”, “Logging from multiple modules”, “Changing the format of displayed messages”, and “Displaying the date/time in messages”. The supplied `logging` module exposes `FileHandler` and `Formatter` for the named-logger setup.

### E2 — Overall run outcome (easy, ~10 min)

**Goal:** Use `Counter` to count result statuses. Return exactly `{"counts": <ordinary dict of observed statuses and counts>, "overall": <worst status>}`. Worst means `ERROR` before `FAIL` before `PASS`, regardless of input order. Include only observed statuses in `counts`. Empty input returns `{"counts": {}, "overall": "PASS"}`: this helper treats a run with no failed checks as passing.

**Signature:** `def summarize(results: list[dict[str, Any]]) -> dict[str, Any]`

**Example:** Two PASS results and one FAIL result → `{"counts": {"PASS": 2, "FAIL": 1}, "overall": "FAIL"}`. Dictionary key order does not matter.

**Watch out:** Count checks, not distinct channels: repeated checks on one channel count separately. Status severity is a stated rule, not alphabetical order or the most frequent status.

**Reread:** `collections` → “Counter objects”; Logging HOWTO → “When to use logging” for the related idea of event importance. Result statuses here are separate from logging levels.

### E3 — Operator failure list (easy, ~9 min)

**Goal:** Use `defaultdict(list)` to collect messages from FAIL and ERROR results under their channel names. Return an ordinary dictionary mapping each affected channel to its list of messages. Omit PASS results and channels without failures. Within each channel, keep input order and repeated or empty messages. Empty input returns `{}`.

**Signature:** `def failures_by_channel(results: list[dict[str, Any]]) -> dict[str, list[str]]`

**Example:** FAIL `CH1: voltage low`, PASS `CH2: ready`, ERROR `CH1: timeout` → `{"CH1": ["voltage low", "timeout"]}`.

**Watch out:** Each channel needs its own list. A message reports what happened; it need not be unique. Dictionary key order does not matter.

**Reread:** `collections` → “defaultdict objects” and its examples of grouping values into lists; Logging HOWTO → “Logging variable data”.

### E4 — Save the run report (medium, ~14 min)

**Goal:** Write a UTF-8 JSON file containing exactly the top-level keys `meta`, `summary`, and `results`. `summary` is E2's output, and `results` is the original list with its order and all fields preserved. `meta` is a copy of the supplied metadata with `generated_utc` added (or replaced). Return `None` and overwrite any existing report file.

**Signature:** `def write_report(results: list[dict[str, Any]], path: str | Path, meta: dict[str, Any], *, now: datetime | None = None) -> None`

**Example:** With `results=[]`, `meta={"station": "A1"}`, and `now=datetime(2026, 10, 28, 12, 30, tzinfo=timezone.utc)`, the decoded file is `{"meta": {"station": "A1", "generated_utc": "2026-10-28T12:30:00+00:00"}, "summary": {"counts": {}, "overall": "PASS"}, "results": []}`.

**Watch out:** When `now` is supplied, it is always an aware datetime. Convert it to UTC and use `.isoformat()` (retain fractional seconds if present; use `+00:00`, not `Z`). When omitted, obtain the current aware UTC datetime with `datetime.now(timezone.utc)`. `generated_utc` belongs inside `meta`, not beside it. Never add it to the caller's metadata. JSON indentation and escaping are up to you; tests decode the file. Reuse `summarize` instead of repeating E2's logic.

**Reread:** Logging HOWTO → “Displaying the date/time in messages” for why timestamps help investigations; `collections` → “Counter objects” for the embedded summary. The supplied `json`, `datetime`, and `timezone` imports support the report. Pro Git 3.5 → “Tracking Branches” and 3.6 → “The Basic Rebase” are today's workflow reading; this set does not run Git commands.
