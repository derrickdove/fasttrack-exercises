# check45 — Final timed station check

**Time:** about 153 minutes · **Read first:** review day - no new reading; revisit the earlier readings named under each exercise · **You edit:** `starter/check45.py`

## What you're building

You are checking software for a chassis test station before an operator uses it. These ten new tasks cover configuration, instrument control, measurement decisions, telemetry, test execution, reports, operator commands, Linux deployment settings, and hardware safety. Everything runs offline with fake instruments; no hardware or administrator access is needed.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/check45.py`. Don't edit `tests/`. The supplied `Transport` interface describes an adapter; you do not need to implement its methods. The two supplied data classes are already complete.
2. Press **Ctrl+Shift+B -> Test: check45** (or run `bash tools/run.sh check45` / `tools\run.ps1 check45`). At first you'll see `Exercises: 0 / 10 passed`. Rerun after each exercise.
3. Use a 153-minute timer, including reading and test runs. Record the exercises you finish and where you stop. Report **all pass / partial / stuck** in the tracker; use the reread notes afterward.

Exercises are independent: attempt any one without completing the others. Only E2's methods belong together. Configuration values from E1 do not automatically control E2 or E8.

A **contract** says what a function accepts, returns, and does when something goes wrong. A **callable** is something you can call like a function; `Callable[[], str]` takes no arguments and returns text. A **data class** holds data in named fields; the supplied frozen data classes cannot have fields reassigned. A **protocol** describes methods an object must provide, so a small fake can stand in for hardware.

```python
from collections.abc import Callable

def display_label(read_label: Callable[[], str]) -> str:
    return "Station: " + read_label()

label = display_label(lambda: "BENCH-9")
```

Unless stated otherwise, arguments have the annotated types; integer arguments are actual integers, not booleans. Do not modify caller-owned lists or dictionaries. Exception message text is your choice. **Finite** means a number other than NaN (not a number) or positive/negative infinity; `math.isfinite` checks this. A **boundary** is the first or last allowed value; tests include these and invalid inputs.

## Exercises

### E1 - Validate a station configuration (medium, ~15 min)

**Goal:** Reject mistakes in a **configuration**, the settings supplied before a station run.

**Signature:** `def validate_config(raw: dict[str, object]) -> StationConfig`

Require exactly these four keys. Raise `ValueError` for a missing/extra key or invalid value:

- `station`: a string nonempty after stripping surrounding whitespace.
- `timeout_ms`: an integer from 1 through 5000 inclusive. A **timeout** limits how long an operation may wait; a millisecond is 1/1000 second.
- `retries`: an integer from 0 through 2 inclusive. A **retry** repeats an operation after failure.
- `channels`: a nonempty list of strings. Strip surrounding whitespace from each name, reject empty names, and reject duplicates after stripping. Compare names case-sensitively; preserve their order.

For this dynamically typed dictionary, reject booleans, floats, and numeric strings where integers are required. Return the supplied `StationConfig(station, timeout_s, retries, channels)` with the stripped station name, milliseconds converted to seconds, and channel names in a tuple (an ordered collection that cannot be changed).

**Example:** `{"station": " B9 ", "timeout_ms": 250, "retries": 1, "channels": [" bus "]}` -> `StationConfig("B9", 0.25, 1, ("bus",))`.

**Watch out:** This function does no input/output (I/O), meaning file or device access.

**Reread:** If you failed E1, reread **d39**, `tomllib` documentation and configuration validation; **d03**, Python Tutorial section 5 (lists, dictionaries, sets, tuples); **d08**, the `typing` introduction.

### E2 - Drive a supply from the station config (medium, ~25 min)

**Goal:** Build a **driver**, software that turns operations into instrument commands, from a station configuration dictionary. This checkpoint combines config validation, a voltage limit, a timeout retry, and automatic cleanup; it does not load a file.

**Signatures:** `StationSupply.from_config(config: dict[str, object], rm: ResourceManagerLike) -> StationSupply` is a `@classmethod`, a method called on the class that creates an instance. Methods: `read_voltage() -> float`, `set_voltage(volts: float) -> None`, `enable_output(on: bool) -> None`, and `close() -> None`; also implement `__enter__` and `__exit__` for `with` blocks. The constructor stores an already-configured resource and its maximum voltage; use `from_config` to create the supply.

The supplied `ResourceManagerLike` and `ResourceLike` protocols and `VisaTimeout(Exception)` are complete; do not implement them. A **resource manager** opens an instrument connection with `open_resource(name)`. Its returned **resource** has writable `timeout`, `read_termination`, and `write_termination` attributes, plus `write(cmd)`, `query(cmd) -> str`, and `close()` methods. A **termination** is the character marking the end of a command or reply. A read timeout is either the supplied `VisaTimeout` or a real `pyvisa.errors.VisaIOError` whose `error_code` equals `pyvisa.constants.StatusCode.error_timeout`. Other VISA error codes are not timeouts.

- `from_config`: accept only `ip`, `timeout_ms`, and `max_voltage`. Require `ip` to be a nonempty string and use it unchanged. `timeout_ms` is optional, defaults to 2000, and must be a positive integer; reject booleans, floats, and numeric strings. A millisecond is 1/1000 second. Require `max_voltage` to be a positive finite `int` or `float`; reject booleans and numeric strings. A missing required key, unknown key, or invalid value raises `ValueError` naming that key. Validate everything before opening anything, without changing the dictionary.
- Then call `rm.open_resource(f"TCPIP::{ip}::INSTR")`. This **VISA resource string** identifies an instrument reached over TCP/IP through PyVISA. Set the resource's `timeout` to `timeout_ms` and both terminations to `"\n"` (one newline character). Do not send commands while configuring it. The tests supply the manager; do not create your own manager, threads, sleeps, or network connection.
- `read_voltage`: query `"MEAS:VOLT?"`, a SCPI command (Standard Commands for Programmable Instruments) asking for measured voltage. Convert the numeric reply with `float` and return volts; there is no unit suffix. Retry exactly once on either timeout described above, using the same command. A second timeout propagates. A non-numeric reply raises `ValueError` without retrying; other query exceptions propagate without retrying.
- `set_voltage`: require a finite value, then round it to three decimal places using `f"{volts:.3f}"`. The rounded value must be from zero through `max_voltage`, inclusive; otherwise raise `ValueError` before any write. Write exactly `f"VOLT {volts:.3f}"`. Check the rounded value, not the original input: with `max_voltage=12.3456`, `set_voltage(12.3456)` must raise because it would command `12.346`; with `max_voltage=12.5`, `set_voltage(12.5001)` writes `"VOLT 12.500"`. A tiny negative input that formats as `"-0.000"` is zero and is allowed.
- `enable_output`: require exactly a `bool`; write `"OUTP 1"` for `True` and `"OUTP 0"` for `False`. Anything else, including integers 0 and 1, raises `TypeError` before any write. Type hints do not enforce runtime checks, and `bool` is a subclass of `int` in Python.
- Context manager: `__enter__` returns the supply. On exit, write `"OUTP 0"`, then call `close()`, always attempting close even if the write fails. Never swallow or replace the block's exception, including when cleanup also fails. With no block exception, cleanup errors propagate; if both write and close fail, the close error propagates.
- `close`: release the resource at most once; repeated calls are no-ops, including after context exit. Mark it closed even if the resource's close call raises. Calling `close()` alone sends no command.

**Example:** with config `{"ip": "192.0.2.45", "max_voltage": 12.5}`, the manager opens `"TCPIP::192.0.2.45::INSTR"` with timeout 2000 and newline terminations. `set_voltage(3.3125)` writes `"VOLT 3.312"`; a query reply `"3.3125"` returns `3.3125`. In this example, the first query raises `VisaTimeout` and the second returns that reply:

```python
with StationSupply.from_config(config, rm) as supply:
    supply.set_voltage(3.3125)
    supply.enable_output(True)
    voltage = supply.read_voltage()  # 3.3125, after one retry
```

The writes, in order, are `"VOLT 3.312"`, `"OUTP 1"`, `"OUTP 0"`; the resource is then closed once.

**Watch out:** Validate config before opening, and distinguish a read timeout from a bad reply. This exercise uses its own supply config; it does not consume E1's `StationConfig`.

**Reread:** If you failed E2, reread **d17**, the `Psu` class exercises E5-E6, PyVISA resource strings, and terminations; **d18**, cleanup; **d05**, exceptions; **d08**, type hints are not runtime checks.

### E3 - Judge measurement evidence (medium, ~12 min)

**Goal:** Perform **result checking**, comparing measurements to limits and distinguishing bad evidence from a failed device.

**Signature:** `def judge_samples(samples: list[float], low: float, high: float, required: int) -> str`

First raise `ValueError` unless both limits are finite, `low <= high`, and `required >= 1`. Then choose the first applicable result:

1. `"ERROR"` if any sample is nonfinite.
2. `"INCOMPLETE"` if fewer than `required` samples were collected.
3. `"FAIL"` if any sample is below `low` or above `high`.
4. `"PASS"` otherwise.

Limits are inclusive, and equal limits are allowed. Examine every supplied sample, including those beyond the required count. An empty list is incomplete.

**Example:** `judge_samples([3.0, 3.6], 3.0, 3.6, 2)` -> `"PASS"`; `[99.0]` with the same limits and count -> `"INCOMPLETE"`.

**Watch out:** One NaN sample returns `"ERROR"` even if three samples were required.

**Reread:** If you failed E3, reread **d02**, Python Tutorial sections 4.1-4.8 (conditions, loops, functions); **d06**, `dataclasses` and `enum` documentation (result states); **d09/d11**, pytest assertions and parametrization (running one test against several inputs).

### E4 - Decode a maintenance telemetry snapshot (medium, ~20 min)

**Goal:** Decode **telemetry**, measurements and status sent by a device. A **packet** is one complete message represented as bytes, numbers from 0 through 255.

**Signature:** `def decode_snapshot(packet: bytes) -> Snapshot`

This exercise uses its own eight-byte FC maintenance format, independent of other sets' formats. Multi-byte numbers are unsigned (never negative) and big-endian (the most significant byte comes first):

| Byte offset (starting at 0) | Meaning |
| --- | --- |
| 0-1 | Literal bytes `b"FC"`, identifying this format |
| 2-3 | 16-bit sequence number, 0-65535 |
| 4-5 | 16-bit voltage in millivolts, 0-65535 |
| 6 | Flags: bit 0 = output on; bit 3 = overtemperature |
| 7 | Checksum: XOR of bytes 0 through 6 |

A **bit** is one binary digit. Bit 0 has value 1 (`0x01`); bit 3 has value 8 (`0x08`). The `0x` prefix means hexadecimal (base 16). Other flag bits are reserved and must be zero. **XOR**, written `^`, combines bits that differ; start at zero and XOR the first seven bytes to compute the checksum, a value used to detect corruption. `struct.unpack` format `">2sHHBB"` matches the layout.

Return the supplied `Snapshot(sequence, voltage_v, output_on, overtemp)`, converting millivolts to volts and flags to booleans. Raise `ValueError` for a length other than eight, wrong identifier, bad checksum, or reserved bits set. Do not accept extra bytes.

**Example:** `bytes.fromhex("4643002a0ce409ce")` -> `Snapshot(42, 3.3, True, True)`.

**Watch out:** Validate flags even with a correct checksum.

**Reread:** If you failed E4, reread **d15**, Python strings versus bytes; **d23**, `struct` documentation (byte order and format characters); **d40**, learncpp O.2/O.3 (bitwise operations). The checksum rule above is supplied for this new format.

### E5 - Audit delivery across sequence wraparound (medium, ~15 min)

**Goal:** Count lost or repeated snapshots using a **sequence number**, a counter advancing by one per sent packet and wrapping from 65535 to zero.

**Signature:** `def audit_sequences(sequences: list[int]) -> dict[str, int]`

Return exactly `{"accepted": ..., "missing": ..., "duplicates": ..., "stale": ...}`, starting all counts at zero. Each input must be between 0 and 65535 inclusive; otherwise raise `ValueError`.

Accept the first number as the baseline, with no missing count before it. For each later number calculate `delta = (number - latest_accepted) % 65536`:

- `delta == 0`: increment duplicates; keep the baseline.
- `1 <= delta < 32768`: increment accepted, add `delta - 1` to missing, update the baseline.
- `32768 <= delta <= 65535`: increment stale; keep the baseline. **Stale** here means too old or ambiguous to advance the counter.

**Example:** `[65535, 1, 1, 0, 2]` -> `{"accepted": 3, "missing": 1, "duplicates": 1, "stale": 1}`.

**Watch out:** An older duplicate counts as stale; only equality with the latest accepted number is a duplicate. Exactly half the counter range is stale.

**Reread:** If you failed E5, reread **d24**, "Serial number arithmetic" (RFC 1982 section 3 is optional); **d03**, Python Tutorial section 5 (dictionary counters); **d13**, Big O chapters (how work grows with input size). One pass is enough.

### E6 - Execute steps with guaranteed cleanup (medium, ~17 min)

**Goal:** Write an **executor**, code that calls test steps in order and records results. A **callback** is a function supplied for other code to call; each action and cleanup is a callback.

**Signature:** `def execute_steps(steps: list[tuple[str, Callable[[], str]]], cleanup: Callable[[], None]) -> list[tuple[str, str]]`

Inputs have unique, nonempty step names. Call actions without arguments. `"PASS"` continues; `"FAIL"` stops further actions. Any other return string, or any exception inheriting from `Exception`, records `"ERROR"` and stops further actions. Include remaining names as `"SKIP"` without calling their actions. Return one `(name, status)` pair per input step, in input order.

Always call `cleanup()` exactly once, after actions and before returning, even for an empty sequence. Do not hide cleanup exceptions. Do not catch `BaseException` subclasses such as `KeyboardInterrupt` (the interruption raised by Ctrl+C); they propagate after cleanup.

**Example:** actions returning PASS, FAIL, PASS -> `[("rail", "PASS"), ("load", "FAIL"), ("sense", "SKIP")]`; sense never runs.

**Watch out:** Cleanup belongs in `finally`, which runs even when control leaves through an exception.

**Reread:** If you failed E6, reread **d33**, "Finite-state machine" (states and transitions); **d18**, Python Tutorial section 8.7; **d27**, `threading` documentation on clean shutdown. This executor is sequential and needs no threads.

### E7 - Save a requirement evidence report (medium, ~13 min)

**Goal:** Create **traceability**, a link from a requirement (something the station must verify) to the steps providing evidence. Store it as JSON, a text format for nested lists, dictionaries, and basic values.

**Signature:** `def write_run_report(path: Path, station: str, rows: list[tuple[str, str]], requirement_steps: dict[str, list[str]]) -> None`

`Path` is a `pathlib` filesystem path. Rows have unique step names and statuses from PASS, FAIL, ERROR, SKIP. `requirement_steps` maps requirement IDs to step-name lists; names may be absent from rows. Inputs already satisfy these type/status rules.

Write exactly these top-level fields:

- `station`: the station string unchanged.
- `steps`: every row in original order as `{"name": name, "status": status}`.
- `requirements`: every supplied ID mapped to its aggregate status. Use priority ERROR, then FAIL, then NOT_RUN, then PASS. A missing step is treated like SKIP. Use NOT_RUN if any listed step is skipped/missing or if the requirement's list is empty; otherwise all passing steps yield PASS.

Create parent directories as needed; overwrite existing files. Use UTF-8, `json.dumps` with two-space indentation and sorted dictionary keys (default ASCII escaping), followed by exactly one LF newline (`\n`), including on Windows. Propagate file errors.

**Example:** rows `[("rail", "FAIL")]`, mapping `{"REQ-7": ["rail", "unseen"]}` -> requirement status `"FAIL"`. An empty mapping produces `"requirements": {}`.

**Watch out:** Unmapped steps still belong in `steps`. Do not invent timestamps or machine-specific fields.

**Reread:** If you failed E7, reread **d44**, NASA Systems Engineering Handbook section 5.3, "Product Verification"; **d04**, `json` and `pathlib` documentation; **d12**, structured reports and Logging HOWTO.

### E8 - Provide the operator command boundary (medium, ~16 min)

**Goal:** Implement a **CLI** (command-line interface), where an operator supplies options and automation receives an exit code, an integer indicating success or failure.

**Signature:** `def main(argv: list[str], run: Callable[[Path], str], out: TextIO, err: TextIO) -> int`

Use `argparse`, Python's command-line parser, with program name `station-check`. `argv` contains option strings without a program name. Support required `--config PATH`, optional `--dry-run`, and standard `-h`/`--help`. Use normal argparse parsing/error behavior; no positional arguments. `TextIO` means a writable text stream; tests use in-memory streams instead of a terminal.

- Help: write argparse help to `out`, return 0, do not call `run`; config is not required for help.
- Missing/bad arguments: write argparse usage and error text to `err`, return 2, do not call `run`. Do not let argparse's `SystemExit` escape.
- Valid dry run: write exactly `"DRY RUN <path>\n"` to `out`, return 0, do not call `run` or check if the path exists. Render `<path>` with `str(Path(argument))`, using native path formatting.
- Valid normal run: call `run(Path(argument))` exactly once. For PASS, FAIL, ERROR, write `"RESULT <status>\n"` to `out` and return 0, 1, 2 respectively. Any other string or any `Exception` from `run` becomes ERROR with exit code 2. Do not catch `BaseException` subclasses.

Dry/normal runs write nothing to `err`. Usage errors write nothing to `out`; help writes nothing to `err`. Exact argparse wording is not graded. The callback owns config loading and hardware work; this is the callable CLI boundary, without a script entry point.

**Example:** `main(["--config", "shift.toml"], lambda path: "FAIL", out, err)` -> code 1 and `"RESULT FAIL\n"` in `out`.

**Watch out:** Do not read `sys.argv` or print to the real terminal. `contextlib.redirect_stdout` and `redirect_stderr` can route argparse output to supplied streams.

**Reread:** If you failed E8, reread **d32**, Python "Argparse Tutorial"; **d29**, `subprocess` documentation (exit codes); **d05**, Python Tutorial section 8 (exceptions).

### E9 - Review an offline Linux service definition (easy, ~10 min)

**Goal:** Check a systemd service definition, a Linux text file describing a background process managed by the operating system. Only inspect text; do not start services. Tests also work on Windows.

**Signature:** `def service_findings(text: str) -> list[str]`

Parse this INI-style text (named `[sections]` containing `key=value` settings) with `configparser`, interpolation disabled so `%i` stays literal. Treat section and setting names as case-sensitive. Raise `ValueError` for syntax errors. Inputs contain no DEFAULT section or multiline values; duplicate settings/sections count as syntax errors. Ignore unrelated sections/settings.

Return failed setting names, once each, in this order:

1. `User`: missing, empty, or exactly `root`. This is the account running the service; root is the administrator account.
2. `ExecStart`: missing/empty or its stripped value does not start with `/`. This specifies the program to start; require an absolute Linux path.
3. `Restart`: not exactly `on-failure`, the policy to restart a failed process.
4. `NoNewPrivileges`: not exactly `true`, preventing the process from gaining additional privileges.

Use values after `configparser` strips surrounding whitespace. Missing `[Service]` means all four findings. An empty list passes this limited policy check; do not check executable existence.

**Example:** `"[Service]\nUser=root\nExecStart=station\nRestart=always\nNoNewPrivileges=false\n"` -> `["User", "ExecStart", "Restart", "NoNewPrivileges"]`.

**Watch out:** Python's config parser normally changes setting names to lowercase. A small subclass overriding `optionxform` can preserve case without changing a method on an existing object.

**Reread:** If you failed E9, reread **d36**, `systemd.service`, `systemd.unit`, and `configparser` documentation; **d31**, *The Linux Command Line* chapters on shell scripts (absolute paths); **d38**, deployment configuration review.

### E10 - Explain hardware interlocks and stale data (easy, ~10 min)

**Goal:** Decode an **interlock**, a condition inhibiting energizing hardware. A **register** is a small hardware value whose individual bits represent status.

**Signature:** `def interlock_reasons(status: int, telemetry_age_s: float, max_age_s: float) -> list[str]`

First raise `ValueError` if status is outside 0-255, age is nonfinite/negative, or maximum age is nonfinite/nonpositive. Age is seconds since telemetry arrived.

Return applicable strings in exactly this order:

- `"DOOR_OPEN"` if bit 0 (`0x01`) is clear (zero); a set bit means the door is closed.
- `"ESTOP"` if bit 2 (`0x04`) is set; an emergency stop is active.
- `"SUPPLY_FAULT"` if bit 7 (`0x80`) is set.
- `"STALE"` if `telemetry_age_s > max_age_s`. Equality is fresh.

Ignore other bits; these flags are separate from E4's packet flags. Return `[]` if no condition inhibits hardware.

**Example:** `interlock_reasons(0x84, 2.0, 1.0)` -> `["DOOR_OPEN", "ESTOP", "SUPPLY_FAULT", "STALE"]`.

**Watch out:** The door bit has the opposite interpretation from the fault bits.

**Reread:** If you failed E10, reread **d40**, learncpp O.2/O.3 (bitwise operators and masks); **d43**, hardware/software debugging and the supplied datasheet; **d02**, Python Tutorial section 4.1 (conditions).

## If you failed Ek, reread dXX

| Exercise | Reread |
| --- | --- |
| E1 | d39 (config validation), d03 (collections), d08 (typing) |
| E2 | d17 (the Psu class exercises E5-E6, PyVISA resource strings, terminations), d18 (cleanup), d05 (exceptions), d08 (type hints are not runtime checks) |
| E3 | d02 (conditions and functions), d06 (result states), d09/d11 (pytest) |
| E4 | d15 (bytes), d23 (struct), d40 (bitwise operations) |
| E5 | d24 (sequence arithmetic), d03 (dictionary counters), d13 (Big O) |
| E6 | d33 (states), d18 (cleanup), d27 (clean shutdown) |
| E7 | d44 (verification), d04 (JSON and paths), d12 (reports) |
| E8 | d32 (argparse), d29 (exit codes), d05 (exceptions) |
| E9 | d36 (systemd and configparser), d31 (absolute paths), d38 (deployment) |
| E10 | d40 (bit masks), d43 (hardware debugging), d02 (conditions) |
