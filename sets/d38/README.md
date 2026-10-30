# d38 — Operator CLI with argparse

**Time:** about 45 minutes · **Read first:** [Python Argparse Tutorial](https://docs.python.org/3/howto/argparse.html) (help, errors, and subcommands), [argparse documentation: Sub-commands](https://docs.python.org/3/library/argparse.html#sub-commands), and **Usability for operators: clear errors, safe prompts, no stack traces** — "Reread your CLI's error messages as if you were a technician at 2 a.m. Fix any that would confuse you." · **You edit:** `starter/opcli.py`

## What you're building

A **test station** is the bench of instruments and software used to check hardware. You will give its technician a **command-line interface (CLI)**: a tool controlled by typed commands. This set uses supplied simulated voltage readings, so no hardware is connected or switched on.

## How this works

1. Replace the four `raise NotImplementedError(...)` lines in `starter/opcli.py`. Keep the supplied `STATIONS`, `_OperatorParser`, and `_run_station`; don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d38** (or run `bash tools/run.sh d38` / `tools\run.ps1 d38` from the repository root). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise. E2 uses E1; E3 and E4 can be solved independently.
3. Report **all pass / partial / stuck** in the tracker.

An **argument** is one piece of command-line text; `argv` is a list of those strings without the program name. An **option** is a named argument such as `--station`; a **subcommand** such as `run` selects an action. `argparse` is Python's standard-library argument parser; `parse_args` returns a **Namespace**, an object holding parsed values as attributes. A **flag** such as `--dry-run` becomes a Boolean (True/False) rather than consuming a value.

**stdout** is the normal output stream; **stderr** is the stream for problems (`print(message, file=sys.stderr)`). An **exit code** is an integer telling a caller how the command ended. `SystemExit` is the exception argparse uses after printing help; a **traceback** is Python's internal error listing, which an operator should not have to read.

```python
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--channel", default="CH1")
args = parser.parse_args(["--channel", "CH2"])
print(args.channel)  # CH2
```

The supplied station dictionary preserves this order: `bench-A` reads `5.0` volts (V), `bench-B` reads `4.0` V, and `bench-offline` reads `None`, meaning the instrument cannot provide a measurement. A **limit** is an acceptable bound: supplied `_run_station(limits_path, station, dry_run)` reads a **UTF-8** (a text encoding) **JSON** (a format for storing data as text) file such as `{"low": 4.5, "high": 5.5}`. It accepts exactly those two keys with **finite** numbers (neither infinity nor NaN, meaning not-a-number), excluding Booleans, and requires `low <= high`. Bounds are inclusive: equality passes.

The helper returns `PASS` (inside bounds), `FAIL` (outside), or `ERROR` (offline). A **dry run** validates the file but does not measure; the helper returns `READY` even for an offline station. Missing/unreadable files raise `OSError`; invalid encoding, JSON, or limits raise `ValueError`. These helpers are complete; your work is the operator interface.

## Exercises

### E1 — Give the operator three commands (easy, ~12 min)

**Goal:** Build an argparse parser with these commands.

**Signature:** `def build_parser() -> argparse.ArgumentParser`

Use the supplied `_OperatorParser` instead of `argparse.ArgumentParser`. It changes argparse's `error(message)` behavior to raise `ValueError(message)` without printing or exiting; that lets E2 produce one clear error line. Subparsers created with `add_parser` automatically use this same parser class.

| Command | Required arguments | Optional arguments |
| --- | --- | --- |
| `run` | `--limits PATH --station NAME` | `--dry-run` |
| `list` | none | none |
| `show` | `--station NAME` | none |

- Set the program name (`prog`) to `station`. Require a subcommand and store it as `args.command`.
- Store `limits` and `station` as strings. Accept only station names from `STATIONS` for both `run` and `show`.
- `args.dry_run` is `False` by default and `True` when the flag appears. Options may appear in either order after the subcommand; paths and names stay as supplied.
- Keep standard `-h` / `--help` support at the top level and for every subcommand. Top-level help names all three commands; run help explains its three options.
- Missing required arguments, unknown subcommands/stations/options, and unexpected positional text raise `ValueError` without output. Do not replace standard help: it prints help to stdout and raises `SystemExit(0)`.

**Example:** `build_parser().parse_args(["run", "--limits", "rail limits.json", "--station", "bench-A", "--dry-run"])` gives attributes `command="run"`, `limits="rail limits.json"`, `station="bench-A"`, `dry_run=True`.

**Watch out:** An option that is required for `run` must not become required for `list`.

**Reread:** Argparse Tutorial, "Introducing Positional Arguments" and "Introducing Optional Arguments"; argparse documentation, "Sub-commands" (`add_subparsers`, `dest`, `required`).

### E2 — Return useful outcomes, not tracebacks (medium, ~17 min)

**Goal:** Dispatch the parsed command and translate outcomes into exit codes. **Dispatch** means choosing the code for the requested subcommand.

**Signature:** `def main(argv: list[str] | None = None) -> int`

Call `build_parser().parse_args(argv)`. Passing `None` uses the real command-line arguments. Return an integer; do not exit from inside `main`.

| Request / outcome | Exact output (each ends in a newline) | Return |
| --- | --- | --- |
| `list` | One name per line on stdout, in `STATIONS` order | `0` |
| `show --station NAME` | `NAME: VALUE V`, or `NAME: offline` if its reading is `None`, on stdout | `0` |
| `run` → helper returns `PASS` | `NAME: PASS` on stdout | `0` |
| `run` → helper returns `FAIL` | `NAME: FAIL` on stdout | `1` |
| `run --dry-run` → `READY` | `NAME: READY` on stdout | `0` |
| `run` → helper returns `ERROR` | `error: NAME: measurement unavailable` on stderr | `2` |
| Bad usage, or helper raises `ValueError` / `OSError` | `error: MESSAGE` on stderr | `3` |
| Top-level or subcommand help | argparse's help on stdout | `0` |

For `run`, call `_run_station(args.limits, args.station, args.dry_run)` exactly once. Use the supplied dictionary directly for `list` and `show`; neither reads a file. `show` uses the ordinary string form of the reading (for example `bench-A: 5.0 V`). Neither `main` nor its run helper asks for confirmation; E4 practices that separately.

On errors, stdout must be empty. On success, FAIL, dry run, or help, stderr must be empty. For usage/input errors, MESSAGE is the exception text with whitespace collapsed to single spaces and leading/trailing whitespace removed (for example, `" ".join(str(error).split())`). This keeps every error to exactly one `error:` line, even if the original exception contains newlines. Keep the useful diagnostic, including any filename in the exception. Do not print usage or a traceback with an error. Catch help's `SystemExit(0)` and return `0` after argparse prints its help.

**Example:** With `{"low": 4.5, "high": 5.5}` in `rail.json`, `main(["run", "--limits", "rail.json", "--station", "bench-B"])` prints `bench-B: FAIL` and returns `1`.

**Watch out:** Code `2` means the test system could not measure; code `3` means fix the command or input file. This follows the capstone's block 5 code meanings. `_OperatorParser` supplies the needed hook because argparse normally exits with code 2 on bad usage.

**Reread:** Argparse Tutorial, the missing-argument/error examples and `--help` examples; argparse documentation, "Sub-commands"; **Usability for operators**, reread every error as a technician at 2 a.m.

### E3 — Align station results (easy, ~9 min)

**Goal:** Format a terminal table, a text grid whose column starts line up. This helper returns text; it does not print and is independent of E2's fixed outputs.

**Signature:** `def format_table(rows: list[dict[str, object]], columns: list[str]) -> str`

The `columns` list gives dictionary keys, their display order, and the header labels. For each cell use `str(row.get(column, ""))`: a missing key becomes empty text; an explicit `None` becomes `"None"`. Ignore keys absent from `columns`. Preserve row order and do not change either input.

Each column's width is the longest string length among its header and cells. **Left-align** means add spaces to the right of shorter cells until they reach that width; `str.ljust(width)` does this. Join padded columns with two spaces, strip trailing spaces from each completed line, then join lines with `"\n"`. Include the header first, no separator line, and do not append an extra newline. A fully empty final row is an empty final line, so that special case naturally ends with `"\n"`. Empty rows still produce the header; empty columns produce `""` regardless of rows. Inputs contain printable ASCII (ordinary terminal characters) with no embedded whitespace in headers or cell strings; string length is sufficient here.

**Example:** `format_table([{"station": "A", "state": "PASS"}, {"station": "long-bench", "state": "FAIL"}], ["station", "state"])` returns:

```text
station     state
A           PASS
long-bench  FAIL
```

**Watch out:** Measure widths using the header too. Remove trailing spaces when the last cell is missing; do not reorder or modify dictionaries.

**Reread:** **Usability for operators**, check whether a technician can scan station names and results without guessing which value belongs to which column.

### E4 — Ask safely before an operator action (easy, ~7 min)

**Goal:** Ask once for permission before a future station action such as enabling a **power supply's** output (an instrument that provides controlled voltage and current).

**Signature:** `def confirm(prompt: str, input_fn: Callable[[str], str] = input) -> bool`

`Callable[[str], str]` means a function taking one string and returning one string. `input_fn` is **dependency injection**: passing in a function lets tests simulate a person without waiting at the keyboard. With no override, Python's `input` is used.

Call `input_fn` exactly once with `prompt + " [y/N] "`. The capital `N` advertises that doing nothing means no. Strip leading/trailing whitespace from its reply and lowercase it. Return `True` only for `"y"` or `"yes"`; return `False` for every other reply, including an empty reply. If the function raises `EOFError` (**end of file**, meaning input was closed), return `False`. Do not print separately, retry, or perform an action; the supplied input function owns displaying the prompt.

**Example:** `confirm("Enable output?", lambda text: " YES ")` returns `True`. With an empty reply it returns `False`.

**Watch out:** Never treat a nonempty reply such as `"sure"` as consent.

**Reread:** **Usability for operators**, "safe prompts": make the default safe and make the accepted confirmation explicit.
