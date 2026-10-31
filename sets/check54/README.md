# check54 — Final timed station check

**Time:** about 153 minutes · **Read first:** review day - no new reading; revisit the earlier readings named under each exercise · **You edit:** `starter/check54.py`, `starter/test_interlock_learner.py`

## What you're building

You are checking software for a chassis test station before an operator uses it. These ten new tasks cover configuration, instrument control, measurement decisions, telemetry, test execution, reports, operator commands, Linux deployment settings, and hardware safety. Everything runs offline with fake instruments; no hardware or administrator access is needed.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in the two starter files, and repair the supplied `run_interlocked` ordering in E10. Don't edit `tests/`. The supplied `Transport` interface describes an adapter; you do not need to implement its methods. The two supplied data classes are already complete. E2 also supplies scaffolding (working setup code): leave `StationSupply.__init__` and `from_config` as provided. E4 supplies length checking and unpacking; E10 supplies the `OutputSupply` interface and recording fake.
2. Press **Ctrl+Shift+B -> Test: check54** (or run `bash tools/run.sh check54` / `tools\run.ps1 check54`). At first you'll see `Exercises: 0 / 10 passed`. Rerun after each exercise.
3. Use a 153-minute timer: the exercise estimates include 143 minutes of work and a shared 10-minute reading and reruns allowance, counted under E2. Use that allowance to read the contracts and rerun tests as needed. Record the exercises you finish and where you stop. Report **all pass / partial / stuck** in the tracker; use the reread notes afterward.

Exercises are independent: attempt any one without completing the others. E2's methods belong together; E10 joins its own interlock decoder, station harness, and regression tests. A **harness** connects small components into an operation; a **regression test** catches a defect if it returns after a repair. E10 uses a fake supply, so you can complete it before E2. Configuration values from E1 do not automatically control E2 or E8.

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

**Reread:** If you failed E1, reread **d45**, `tomllib` documentation and configuration validation; **d03**, Python Tutorial section 5 (lists, dictionaries, sets, tuples); **d08**, the `typing` introduction.

### E2 - Drive a supply from the station config (medium, ~25 min)

**Time:** 15 minutes of implementation plus the shared 10-minute reading and reruns allowance for the whole set. The supplied setup saves those 10 minutes of implementation.

**Goal:** Complete a **driver**, software that turns operations into instrument commands, using the supplied configuration validation and resource setup. Implement voltage limits, timeout retries, output safety, and automatic cleanup; this exercise does not load a file.

**Supplied:** `StationSupply.from_config(config: dict[str, object], rm: ResourceManagerLike) -> StationSupply` is a `@classmethod`, a method called on the class that creates an instance. The constructor (`__init__`, called when an instance is created) stores the already-configured resource as `self.resource`, its maximum voltage as `self.max_voltage`, and `self._closed`, initially `False`, to record whether close has been attempted. Use `from_config` to create the supply; the setup contract below is already implemented.

**Implement:** `read_voltage() -> float`, `set_voltage(volts: float) -> None`, `enable_output(on: bool) -> None`, and `close() -> None`; also implement `__enter__` and `__exit__` for `with` blocks. Use the supplied fields in these methods.

The supplied `ResourceManagerLike` and `ResourceLike` protocols and `VisaTimeout(Exception)` are complete; do not implement them. A **resource manager** opens an instrument connection with `open_resource(name)`. Its returned **resource** has writable `timeout`, `read_termination`, and `write_termination` attributes, plus `write(cmd)`, `query(cmd) -> str`, and `close()` methods. A **termination** is the character marking the end of a command or reply. A read timeout is either the supplied `VisaTimeout` or a real `pyvisa.errors.VisaIOError` whose `error_code` equals `pyvisa.constants.StatusCode.error_timeout`. Other VISA error codes are not timeouts.

- Supplied `from_config`: accept only `ip`, `timeout_ms`, and `max_voltage`. Require `ip` to be a nonempty string and use it unchanged. `timeout_ms` is optional, defaults to 2000, and must be a positive integer; reject booleans, floats, and numeric strings. A millisecond is 1/1000 second. Require `max_voltage` to be a positive finite `int` or `float`; reject booleans and numeric strings. A missing required key, unknown key, or invalid value raises `ValueError` naming that key. Validate everything before opening anything, without changing the dictionary.
- The supplied setup then calls `rm.open_resource(f"TCPIP::{ip}::INSTR")`. This **VISA resource string** identifies an instrument reached over TCP/IP through PyVISA. Set the resource's `timeout` to `timeout_ms` and both terminations to `"\n"` (one newline character). If setting the timeout or either termination raises, the supplied setup attempts to close the opened resource exactly once and propagates the original setup exception, even if close also raises. Do not send commands while configuring it. The tests supply the manager; do not create your own manager, threads, sleeps, or network connection.
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

**Watch out:** Keep the supplied setup unchanged. Distinguish a read timeout from a bad reply, check the rounded voltage before writing, and attempt close even if disabling output fails. This exercise uses its own supply config; it does not consume E1's `StationConfig`.

**Reread:** If you failed E2, reread **d19**, the `Psu` class exercises E5-E6, PyVISA resource strings, and terminations; **d20**, cleanup; **d05**, exceptions; **d08**, type hints are not runtime checks.

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

**Reread:** If you failed E3, reread **d02**, Python Tutorial sections 4.1-4.8 (conditions, loops, functions); **d06**, `dataclasses` and `enum` documentation (result states); **d09/d12**, pytest assertions and parametrization (running one test against several inputs).

### E4 - Decode a maintenance telemetry snapshot (medium, ~12 min)

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

A **bit** is one binary digit. Bit 0 has value 1 (`0x01`); bit 3 has value 8 (`0x08`). The `0x` prefix means hexadecimal (base 16). Other flag bits are reserved and must be zero. **XOR**, written `^`, combines bits that differ; start at zero and XOR the first seven bytes to compute the checksum, a value used to detect corruption. `struct.unpack` format `">2sHHBB"` matches the layout. **Unpacking** turns packet bytes into named Python values. The starter already checks the length and unpacks `magic`, `sequence`, `millivolts`, `flags`, and `received` (the transmitted checksum). Keep that supplied code; implement the remaining validation and conversion.

Return the supplied `Snapshot(sequence, voltage_v, output_on, overtemp)`, converting millivolts to volts and flags to booleans. Raise `ValueError` for a length other than eight, wrong identifier, bad checksum, or reserved bits set. Do not accept extra bytes.

**Example:** `bytes.fromhex("4643002a0ce409ce")` -> `Snapshot(42, 3.3, True, True)`.

**Watch out:** Validate flags even with a correct checksum.

**Reread:** If you failed E4, reread **d16**, Python strings versus bytes; **d26**, `struct` documentation (byte order and format characters); **d47**, learncpp O.2/O.3 (bitwise operations). The checksum rule above is supplied for this new format.

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

**Reread:** If you failed E5, reread **d27**, "Serial number arithmetic" (RFC 1982 section 3 is optional); **d03**, Python Tutorial section 5 (dictionary counters); **d15**, Big O chapters (how work grows with input size). One pass is enough.

### E6 - Execute steps with guaranteed cleanup (medium, ~17 min)

**Goal:** Write an **executor**, code that calls test steps in order and records results. A **callback** is a function supplied for other code to call; each action and cleanup is a callback.

**Signature:** `def execute_steps(steps: list[tuple[str, Callable[[], str]]], cleanup: Callable[[], None]) -> list[tuple[str, str]]`

Inputs have unique, nonempty step names. Call actions without arguments. `"PASS"` continues; `"FAIL"` stops further actions. Any other return string, or any exception inheriting from `Exception`, records `"ERROR"` and stops further actions. Include remaining names as `"SKIP"` without calling their actions. Return one `(name, status)` pair per input step, in input order.

Always call `cleanup()` exactly once, after actions and before returning, even for an empty sequence. Do not hide cleanup exceptions. Do not catch `BaseException` subclasses such as `KeyboardInterrupt` (the interruption raised by Ctrl+C); they propagate after cleanup.

**Example:** actions returning PASS, FAIL, PASS -> `[("rail", "PASS"), ("load", "FAIL"), ("sense", "SKIP")]`; sense never runs.

**Watch out:** Cleanup belongs in `finally`, which runs even when control leaves through an exception.

**Reread:** If you failed E6, reread **d39**, "Finite-state machine" (states and transitions); **d20**, Python Tutorial section 8.7; **d31**, `threading` documentation on clean shutdown. This executor is sequential and needs no threads.

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

**Reread:** If you failed E7, reread **d53**, NASA Systems Engineering Handbook section 5.3, "Product Verification"; **d04**, `json` and `pathlib` documentation; **d13**, structured reports and Logging HOWTO.

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

**Reread:** If you failed E8, reread **d38**, Python "Argparse Tutorial"; **d33**, `subprocess` documentation (exit codes); **d05**, Python Tutorial section 8 (exceptions).

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

**Reread:** If you failed E9, reread **d41**, `systemd.service`, `systemd.unit`, and `configparser` documentation; **d36**, *The Linux Command Line* chapters on shell scripts (absolute paths); **d44**, deployment configuration review.

### E10 - Use interlocks to block output enable (medium, ~18 min)

**Goal:** Decode an **interlock**, a condition inhibiting energizing hardware, and use that decision before enabling a supply. A **register** is a small hardware value whose individual bits represent status.

**Signature:** `def interlock_reasons(status: int, telemetry_age_s: float, max_age_s: float) -> list[str]`

First raise `ValueError` if status is outside 0-255, age is nonfinite/negative, or maximum age is nonfinite/nonpositive. Age is seconds since telemetry arrived.

Return applicable strings in exactly this order:

- `"DOOR_OPEN"` if bit 0 (`0x01`) is clear (zero); a set bit means the door is closed.
- `"ESTOP"` if bit 2 (`0x04`) is set; an emergency stop is active.
- `"SUPPLY_FAULT"` if bit 7 (`0x80`) is set.
- `"STALE"` if `telemetry_age_s > max_age_s`. Equality is fresh.

Ignore other bits; these flags are separate from E4's packet flags. Return `[]` if no condition inhibits hardware.

**Example:** `interlock_reasons(0x84, 2.0, 1.0)` -> `["DOOR_OPEN", "ESTOP", "SUPPLY_FAULT", "STALE"]`.

**Then repair the harness:**

`def run_interlocked(supply: OutputSupply, read_interlock: Callable[[], tuple[int, float]], max_age_s: float) -> list[str]`

The supplied `OutputSupply` protocol only requires `enable_output(on: bool) -> None`; E2's `StationSupply` also satisfies it. The supplied harness currently calls `enable_output(True)` before checking the interlock. Move that call behind the decision:

- Call `read_interlock()` exactly once per invocation to obtain `(status, telemetry_age_s)`. Always take this new reading; do not reuse a decision from a previous call.
- Pass both values and `max_age_s` to `interlock_reasons`. Return its reason list unchanged.
- Only when that list is empty, call `supply.enable_output(True)` exactly once, after reading and checking. With any reason, make no output calls, even a temporary enable followed by disable. Equality at the age limit is fresh.
- Let read, validation, and output exceptions propagate. A read or validation failure must make no output calls. This harness only decides whether to enable; it does not set voltage, measure, or perform E2's cleanup.

**Write your regressions:** In `starter/test_interlock_learner.py`, keep the supplied `FakeStation` and import `from starter import check54 as station`. This binds `station` to the `check54` module (a Python file). Replace the three test stubs with ordinary assertions; keep their names and signatures with no parameters. An **assertion** (`assert condition`) fails a test when its condition is false. Call `station.run_interlocked(...)` through that module so the grader can substitute the faulty harness. Do not skip tests or mark them as expected failures.

`FakeStation(status, age_s)` supplies both `read_interlock()` and `enable_output(on)`. It records every call in `fake.events`: `("read",)` for a read and `("enable", on)` for an output call, in order. It touches no hardware. Use the fake as the supply and pass `fake.read_interlock` as the callback. In each test, check both returned reasons and the exact event list:

| Test | Status | Age / maximum (seconds) | Expected reasons | Expected events |
| --- | --- | --- | --- | --- |
| `test_e10_fresh` | `0x01` | `1.0 / 1.0` | `[]` | `[("read",), ("enable", True)]` |
| `test_e10_stale` | `0x01` | `1.001 / 1.0` | `["STALE"]` | `[("read",)]` |
| `test_e10_faulted` | `0x81` | `0.0 / 1.0` | `["SUPPLY_FAULT"]` | `[("read",)]` |

The grader runs each test on your repaired harness, then on a **mutant**, a deliberately faulty version that restores the enable-before-check defect. Each regression must pass normally and fail with an assertion on that mutant. Checking only the returned reasons misses the unsafe output call; checking event order also catches the defect with fresh input.

**Watch out:** The door bit has the opposite interpretation from the fault bits. Decoding a reason cannot protect hardware unless the harness uses it before output enable.

**Reread:** If you failed E10, reread **d47**, learncpp O.2/O.3 (bitwise operators and masks); **d51**, hardware/software debugging and the supplied datasheet; **d02**, Python Tutorial section 4.1 (conditions); **d09/d12**, pytest assertions and regression tests.

## If you failed Ek, reread dXX

| Exercise | Reread |
| --- | --- |
| E1 | d45 (config validation), d03 (collections), d08 (typing) |
| E2 | d19 (the Psu class exercises E5-E6, PyVISA resource strings, terminations), d20 (cleanup), d05 (exceptions), d08 (type hints are not runtime checks) |
| E3 | d02 (conditions and functions), d06 (result states), d09/d12 (pytest) |
| E4 | d16 (bytes), d26 (struct), d47 (bitwise operations) |
| E5 | d27 (sequence arithmetic), d03 (dictionary counters), d15 (Big O) |
| E6 | d39 (states), d20 (cleanup), d31 (clean shutdown) |
| E7 | d53 (verification), d04 (JSON and paths), d13 (reports) |
| E8 | d38 (argparse), d33 (exit codes), d05 (exceptions) |
| E9 | d41 (systemd and configparser), d36 (absolute paths), d44 (deployment) |
| E10 | d47 (bit masks), d51 (hardware debugging), d02 (conditions), d09/d12 (pytest regressions) |
