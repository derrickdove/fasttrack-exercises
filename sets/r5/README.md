# r5 — Week 5 review

**Time:** about 60 minutes · **Read first:** no new reading; review d04 (CSV) and d23 (CRC), plus d29–d34: Missing Semester, "Command-line Environment" and "Shell Tools and Scripting"; *The Linux Command Line*, chapters on writing your first script, flow control, and positional parameters; Python's `subprocess`, `signal`, `configparser`, and `tomllib` documentation; freedesktop.org's `systemd.service`, `systemd.unit`, and `journalctl` man pages; Wikipedia's "Finite-state machine" overview; *A Common-Sense Guide to DSA*, graphs chapter; *Pro Git*, branching basics and "Contributing to a Project"; GitHub Docs, "Building and testing Python". · **You edit:** `starter/review5.py` and `starter/station_summary.sh`.

## What you're building

A chassis test station needs to run a diagnostic tool, summarize saved outcomes, check its service settings, and release instrument resources when a sequence stops. This set mixes this week with earlier weeks: process tools and service checks, CSV outcome files, and checked telemetry replies. Finish these independent review tasks, including applying two code-review comments to a measurement checker. These are local simulations: nothing starts a real service or contacts an instrument.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/review5.py`, and replace the unfinished body in `starter/station_summary.sh`. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: r5** (or run `bash tools/run.sh r5` / `tools\run.ps1 r5`). At first you'll see `Exercises: 0 / 7 passed`. Rerun after each exercise.
3. Report all pass / partial / stuck in the tracker. Stop around 60 minutes and report partial if needed.

**Standard output (stdout)** is a program's normal output; **standard error (stderr)** carries diagnostics. An **exit code** is the integer a process (a running program) returns: conventionally zero means success. A **timeout** caps how long the caller waits. An **argument list** passes separate words to a process without asking a **shell** (a command interpreter) to interpret them.

**Bash** is a command interpreter used on Linux; Git Bash also works on Windows. A **positional parameter**, such as `$1`, is a script argument. Quote file arguments so spaces stay inside one path. `set -euo pipefail` stops on unhandled command failures, unset variables, or a failed command in a pipeline (commands connected with `|`). Install Bash or use Codespaces for E2; a skipped exercise counts as unfinished.

An **INI file** groups `key=value` settings under `[section]` headers. A **systemd service** is a background program managed by Linux's service manager; its **unit file** describes how to run it. `configparser` reads INI text. A **state machine** describes named stages and the moves between them. A **callback** is a function passed into another function; **cleanup** releases resources after work stops. A `finally` block runs when execution leaves its matching `try` block, even after an exception. **NaN** means "not a number"; NaN and positive/negative infinity are **nonfinite** values. `math.isfinite(x)` identifies ordinary finite numbers.

```python
from collections.abc import Callable

def call_once(action: Callable[[], None]) -> None:
    action()

call_once(lambda: print("Operator panel connected"))
```

**CSV** (comma-separated values) stores a table with a header naming its columns. `csv.DictReader` yields each row as a dictionary and handles quoted commas. A **set** tracks unique values; keep a separate list when first-seen order matters. **Telemetry** means messages from the device to the station; an **acknowledgment** replies that a message was accepted or rejected. A **CRC** (cyclic redundancy check) is a calculated number used to detect damaged bytes. `zlib.crc32(data)` computes it. **Big-endian** puts the largest-place byte first; `int.from_bytes(raw, "big")` decodes such a number.

## Exercises

### E1 — Capture a station probe (easy, ~10 min)

**Goal:** Run a diagnostic program without a shell and collect its result.

**Signature:** `def run_probe(args: list[str], timeout: float) -> tuple[int, str, str]`

Return `(exit_code, stdout, stderr)`. Use `subprocess.run`, capture both streams as UTF-8 text (a standard way to encode characters as bytes; replace undecodable bytes), and preserve spaces and newlines. Nonzero exits are results, not exceptions. If the process exceeds `timeout` seconds, ensure the child process (the program you launched) is killed and waited for, discard partial output, and return `(-9, "", "timeout")`. `subprocess.run` handles that timeout cleanup for you. Let launch errors such as `FileNotFoundError` propagate. Inputs are a nonempty argument list and a positive timeout; no extra input validation is needed. The child does not start other processes.

**Example:** a program that prints `READY` and exits 0 → `(0, "READY\n", "")`.

**Watch out:** Pass the argument list directly; a semicolon inside an argument is literal text. Don't strip output or raise on a nonzero exit.

**Reread:** d29, Python `subprocess` docs: `run`, `CompletedProcess`, and `TimeoutExpired`; Missing Semester "Command-line Environment", process exit status.

### E2 — Summarize a shift's outcomes (easy, ~8 min)

**Goal:** Write `bash starter/station_summary.sh FILE`. A shift is one operator's work period; each saved outcome occupies one line of a UTF-8 text file.

Require exactly one argument naming an existing regular file, assumed readable. On wrong argument count, missing path, or directory, emit exactly `Usage: bash station_summary.sh FILE\n` to stderr, nothing to stdout, and exit 2. Otherwise count lines equal to `PASS`, `FAIL`, or `ERROR`, with exact case and no surrounding spaces. Ignore all other lines, including blanks. Accept LF (newline) or CRLF (carriage return followed by newline) line endings; remove one final carriage return, and include the last line even without a final newline. Treat file contents as data: never execute them. Produce exactly one stdout line, `PASS=N FAIL=N ERROR=N\n`, and no stderr. Exit 1 if any FAIL or ERROR was counted; otherwise exit 0. An empty file is valid. Include `set -euo pipefail` on its own line before your work.

**Example:** file text `PASS\nFAIL\nPASS\n` → stdout `PASS=2 FAIL=1 ERROR=0\n`, exit 1.

**Watch out:** Quote paths containing spaces. `IFS= read -r line` preserves whitespace and backslashes; add a loop condition for a last line without a newline. An arithmetic assignment such as `count=$((count + 1))` works with `set -e` even when the old count is zero.

**Reread:** d31, Missing Semester "Shell Tools and Scripting", quoting and loops; *The Linux Command Line*, flow control and positional parameters.

### E3 — Review a service file (easy, ~5 min)

**Goal:** Check a small station service policy without running systemd.

**Signature:** `def service_problems(text: str) -> list[str]`

The supplied `_service_settings(text)` helper handles parsing; use its returned dictionary to check the three policy rules. Leave the helper unchanged. It parses INI text with `configparser`, with interpolation (substitution of `%` placeholders) disabled. Section and key names are case-sensitive. Surrounding setting whitespace is removed by the parser. Inputs have no repeated sections/keys or `[DEFAULT]` settings. Allow missing sections and keys; ignore unrelated settings. Check these rules in this order and return the corresponding exact message for each broken rule:

| Rule in `[Service]` | Message |
| --- | --- |
| `User` is present, nonempty, and not exactly `root` or `0` | `User must be non-root` |
| `ExecStart` is present and its value starts with `/` | `ExecStart must be absolute` |
| `Restart` equals `on-failure` | `Restart must be on-failure` |

`User` names the account running the service; numeric user ID `0` is root too. `ExecStart` is its launch command; an **absolute path** here simply starts with `/`. `Restart=on-failure` requests restarting after an unsuccessful exit. Don't check whether the account or command exists. A missing `[Service]` fails all three rules. Malformed INI syntax must propagate a `configparser.Error`, rather than becoming policy messages.

**Example:** `[Service]\nUser=station\nExecStart=/opt/station/probe\nRestart=on-failure\n` → `[]`.

**Watch out:** The supplied parser preserves exact key names and literal percent signs. Use missing-key defaults when checking the policy.

**Reread:** d32, Python `configparser` docs, `read_string`, mapping access, `optionxform`, and interpolation; `systemd.service`, `ExecStart`, `Restart`; `systemd.unit`, section format.

### E4 — Stop a sequence and release instruments (medium, ~11 min)

**Goal:** Record station states and guarantee cleanup after success, failure, or an operator interrupt.

**Signature:** `def run_sequence(steps: list[Step]) -> tuple[str, list[str]]`

The supplied alias `Step` means `(name, run, cleanup)`: a label string, a callback taking no arguments and returning a Boolean (`True` or `False`), and a callback taking no arguments and returning `None`. Names are labels only. Call `run` callbacks in input order. True means continue; False means stop with `FAIL`. An ordinary `Exception` from `run` stops with `ERROR`; `KeyboardInterrupt` (the exception Python uses for Ctrl+C) stops with `ABORTED`. If all runs succeed, including an empty list, finish with `PASS`.

Use the supplied `_cleanup_attempts(cleanups)` helper in your `finally` block: it calls the stored callbacks in reverse order, continues after `Exception` or `KeyboardInterrupt`, and returns True if any such cleanup failed. On True, set the final state to `ERROR`. Leave this helper unchanged; you implement the run loop, exception handling, callback registration, and history.

Always call cleanup once for every attempted run, including the run that returned False or raised. Call these cleanups in reverse attempt order; never clean an unattempted step. If a cleanup raises `Exception` or `KeyboardInterrupt`, continue remaining cleanups and change the final state to `ERROR`, overriding every other outcome. Catch only those exception categories; other `BaseException` subclasses may propagate after cleanup. Do not mutate the input list.

Return `(final_state, history)`. History is a fresh list starting with `IDLE`, `SETUP`, `RUNNING`, followed by the final state exactly once, after cleanup. `IDLE` means waiting, `SETUP` means preparing, `RUNNING` means executing, and PASS/FAIL/ERROR/ABORTED are terminal states: success, failed check, software/resource error, and operator stop. This simplified review has no separate setup callbacks.

**Example:** two runs return True then False; cleanups succeed → `("FAIL", ["IDLE", "SETUP", "RUNNING", "FAIL"])`, with cleanup of the second step before the first.

**Watch out:** Register a cleanup before attempting its run. One cleanup error must not prevent earlier resources from being released. `KeyboardInterrupt` is not a subclass of `Exception`.

**Reread:** d33, Wikipedia "Finite-state machine", states and transitions; *A Common-Sense Guide to DSA*, graphs and directed edges (allowed moves). For E4's cleanup behavior, revisit the d33 sequence exercise; for interrupts, d29's `signal` docs and Missing Semester job control.

### E5 — Apply measurement review comments (easy, ~8 min)

**Goal:** Implement the reviewed limit checker used before a station report is accepted. A **limit** is a permitted measurement boundary; **inclusive** means the boundary itself passes. A **code review** is another developer checking a proposed change before it is merged.

**Signature:** `def review_reading(value: float, low: float, high: float) -> bool`

Review comment 1: "Both boundaries must pass, including a zero-width interval such as [24.0, 24.0]." Review comment 2: "An invalid reading must fail even when comparisons with it behave unexpectedly. Validate the limits before checking the reading."

Raise `ValueError` if either limit is nonfinite or `low > high`. Otherwise return True exactly when `value` is finite and `low <= value <= high`; return False for all other readings, including NaN and either infinity. Inputs are floats; do not convert strings or other types. Do not round measurements. Invalid limits must raise even if the reading is also nonfinite. No particular exception message is required.

**Example:** `review_reading(24.0, 24.0, 28.0)` → `True`; `review_reading(float("nan"), 24.0, 28.0)` → `False`.

**Watch out:** A test checking only an ordinary in-range value misses both review defects. Think of the boundary and NaN cases you would request in a pull request (a proposed change submitted for review).

**Reread:** d34, *Pro Git*, "Contributing to a Project", reviewing proposed changes; GitHub Docs "Building and testing Python", running tests in CI (continuous integration: automatic checks on changes). Revisit d34's two limit-checker review comments and the day 30 limit-validation checkpoint (`check30`).


### E6 — Build the operator's rerun list (easy, ~9 min)

**Goal:** Read a saved outcome CSV and identify channels that need another hardware check. A **channel** is a named instrument input; PASS means accepted, FAIL means outside requirements, and ERROR means no trustworthy result.

**Signature:** `def rerun_channels(path: str | Path) -> list[str]`

Open the file as UTF-8 with `newline=""` and close it on every exit. Paths may be strings or `Path` objects. The header is exactly `channel,status`; each nonblank row has both fields and a nonempty channel. Skip completely empty lines. Use CSV parsing so quoted channel names may contain commas. Preserve channel text exactly, including spaces, capitalization, and non-English characters.

Return each channel with at least one FAIL or ERROR exactly once, ordered by its first FAIL or ERROR row. An earlier PASS does not place it in the list; a later PASS does not remove it. Header-only and all-PASS files return `[]`. Raise `ValueError` for a status other than exactly PASS, FAIL, or ERROR; do not strip or change status text. Let file errors propagate. Do not change the file. No other CSV validation is needed; inputs are structurally valid.

**Example:** Rows `(BUS_V, PASS)`, `(TEMP_C, FAIL)`, `(BUS_V, ERROR)`, `(TEMP_C, PASS)` → `["TEMP_C", "BUS_V"]`.

**Watch out:** A set prevents repeated channels, but returning only a set would lose the required order. Do not split CSV lines at commas.

Reread: d04

### E7 — Check a telemetry acknowledgment (easy–medium, ~9 min)

**Goal:** Reject a damaged reply before the station trusts whether its telemetry message was accepted. This compact reply format is separate from d23's measurement packet.

**Signature:** `def decode_ack(packet: bytes) -> tuple[int, bool]`

Require exactly seven bytes, with this layout (offsets start at zero):

| Offset | Bytes | Meaning |
| --- | --- | --- |
| 0 | 2 | Unsigned sequence number (message counter), big-endian, 0..65535 |
| 2 | 1 | Status: 0 means rejected; 1 means accepted |
| 3 | 4 | Unsigned CRC, big-endian, calculated over the first three bytes only |

Return `(sequence, accepted)`, where `accepted` is a Boolean: False for status 0 and True for status 1. Raise `ValueError` for any other length (including extra bytes), any other status byte, or a CRC unequal to `zlib.crc32(packet[:3])`. No particular exception message or validation order is required. Check length before indexing. Do not decode the bytes as text, check for missing sequences, or contact hardware.

**Example:** A reply whose first three bytes are `b"\x00\x2a\x01"`, followed by their correct four-byte big-endian CRC, returns `(42, True)`. The same sequence with status 0 and a newly calculated CRC returns `(42, False)`.

**Watch out:** The stored CRC is excluded from its own calculation. A status other than 0 or 1 is invalid even with a matching CRC.

Reread: d23
