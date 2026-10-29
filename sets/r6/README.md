# r6 — Week 6 station review

**Time:** about 60 minutes · **Read first:** review day: no new reading; revisit the earlier readings named below · **You edit:** `starter/review6.py`

## What you're building

This set mixes this week's material with new problems from earlier weeks. An operator needs to select a station command, interpret instrument status, and set up instruments in a safe order. You will also parse driver error replies, expose status through a small web service, count logged alarms, and scan supply currents. All work stays in Python; no instrument, network server, container, or C++ compiler is needed. Example IDs use `psu` for a power supply unit, `dmm` for a digital multimeter (a voltage/current measuring instrument), and `scope` for an oscilloscope (a signal viewer).

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/review6.py`. Don't edit `tests/`. Keep the supplied `_setup_graph`, `_health_app`, and `Transport` interface unchanged; their complete code reduces setup work in this review.
2. Press **Ctrl+Shift+B → Test: r6** (or run `bash tools/run.sh r6` / `tools\run.ps1 r6`). At first you'll see `Exercises: 0 / 7 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

Earlier readings used here:

- d04: Python Tutorial §7.2; `csv` documentation (`DictReader`, quoted fields).
- d17: `typing.Protocol` documentation; *The Pragmatic Programmer*, "Decoupling" (drivers and fake transports).

- d36: Python **Argparse Tutorial**; **argparse** documentation, subcommands.
- d37: FastAPI tutorial **First Steps** and **Testing**.
- d39: **tomllib** documentation; *A Common-Sense Guide to DSA*, the chapter on graphs (topological ordering). This review supplies dictionaries, so you do not load a file.
- d40: learncpp **O.2 Bitwise operators**, **O.3 Bit manipulation with bitwise operators and bit masks**, and **13.7 Introduction to structs**; *C++ Primer*, chapter 4, bitwise operators.
- d41: learncpp **12.7 Introduction to pointers** and **14.2 Introduction to classes**; *C++ Primer*, chapter 7, classes. E4 revisits the driver's error-reply boundary in Python.

A **CLI** (command-line interface) accepts words typed in a terminal. A **parser** turns those words into named values. An `argparse.Namespace` stores those values as attributes, such as `args.station`.
A **Boolean** is either `True` or `False`. A **dictionary** maps keys to values. A **type hint**, such as `list[str]`, describes the expected input or output. A **ValueError** signals that a value has the right general type but invalid contents.
An **assertion** checks an expected result; **pytest** runs tests containing those checks.

```python
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--channel", default="CH1")
args = parser.parse_args(["--channel", "CH2"])
assert args.channel == "CH2"
```

## Exercises

### E1 — Select an operator command (easy, ~8 min)

**Goal:** Parse a command without starting a test or contacting hardware.

**Signature:** `def parse_command(argv: list[str]) -> argparse.Namespace`

Use `argparse` with required **subcommands** (the first word selects a different operation):

- `run --station NAME [--dry-run]`: return attributes `command="run"`, `station=NAME`, and `dry_run` as a Boolean, default `False`. A **dry run** previews work without operating hardware; here it is only a parsed flag.
- `show --station NAME --instrument ID`: return attributes `command="show"`, `station=NAME`, and `instrument=ID`.

`argv` contains only argument words, with no program filename. Preserve string values exactly and do not modify the list. Options can appear in either order after their subcommand. Successful parsing prints nothing. Missing required arguments, unknown commands, and unknown options must follow argparse's usual behavior: print a diagnostic to standard error (the terminal's error stream) and raise `SystemExit` with code `2`. Ordinary `--help` keeps argparse's usual help behavior. Error/help wording and irrelevant attributes for the other command are not checked.

**Example:** `parse_command(["run", "--station", "bench-2", "--dry-run"]).dry_run` → `True`

**Watch out:** A store-true flag takes no value. Do not read the real process arguments; parse the supplied `argv`.

**Reread:** d36, Python **Argparse Tutorial**, optional arguments and `store_true`; **argparse** documentation, subcommands (`add_subparsers`).

### E2 — Decode an instrument status byte (easy, ~7 min)

**Goal:** Turn a register (an instrument's stored status number) into named flags. A **bit** is one binary digit, a **byte** contains eight bits, and a **flag** is an on/off condition. A **mask** selects bits using bitwise AND (`&`); `0x` marks hexadecimal (base-sixteen) notation.

**Signature:** `def decode_status(value: int) -> dict[str, bool]`

Inputs are integers, excluding Booleans. Accept `0` through `255`, inclusive; otherwise raise `ValueError` (message unrestricted). Return exactly these four keys, each containing a Python `bool`:

| Key | Mask | Meaning when set |
| --- | --- | --- |
| `ready` | `0x01` (1) | Instrument is ready |
| `output_on` | `0x02` (2) | Power output is enabled |
| `overcurrent` | `0x08` (8) | Current limit was exceeded |
| `overtemperature` | `0x20` (32) | Temperature limit was exceeded |

Ignore all other bits. Multiple flags can be true together.

**Example:** `decode_status(9)` → `{"ready": True, "output_on": False, "overcurrent": True, "overtemperature": False}`

**Watch out:** A bitwise result such as `value & 8` is an integer; convert it to `bool`.

**Reread:** d40, learncpp **O.2 Bitwise operators** and **O.3 Bit manipulation with bitwise operators and bit masks**; *C++ Primer*, chapter 4, bitwise operators.

### E3 — Plan instrument setup (medium, ~8 min)

**Goal:** Return a safe **topological order**: a sequence placing every prerequisite before the item that needs it. A **topology** describes connections; here it is a directed graph whose nodes are instrument IDs and whose connections describe prerequisites.

**Signature:** `def setup_order(deps: dict[str, list[str]]) -> list[str]`

Each dictionary key names an instrument; its list names instruments that must finish setup first. IDs are nonempty strings. Every referenced ID must also be a key. Return each key exactly once. At each step, choose the alphabetically smallest currently ready ID using Python's normal string ordering, including newly ready IDs. Empty input returns `[]`. Repeated prerequisites count once. Do not modify the dictionary or its lists.

Validate references before ordering: if references are missing from the keys, raise `ValueError("unknown prerequisite: X")`, where `X` is the alphabetically smallest missing ID. If a **cycle** (a chain that leads back to itself) prevents completion, raise `ValueError("cycle or blocked: X, Y")`, listing all unprocessed IDs in alphabetical order, joined by comma-space. This includes instruments waiting on a cycle as well as the cycle itself.

**Example:** `setup_order({"psu": [], "dmm": ["psu"], "scope": []})` → `["psu", "dmm", "scope"]`

**Supplied:** Start with `remaining, followers, ready = _setup_graph(deps)`. This helper already removes repeated prerequisites, checks unknown IDs with the required message, and copies the graph state. `remaining[id]` counts unfinished prerequisites; `followers[id]` lists instruments that depend on it. `ready` is a **min-heap**, a list arranged so `heapq.heappop(ready)` removes the smallest name. Use `heapq.heappush(ready, name)` when a count reaches zero. Implement the ordering loop and final cycle check.

**Watch out:** Sorting all the IDs once is insufficient. A newly ready `dmm` must come before an already ready `scope`. Kahn's algorithm repeatedly removes a ready node; `heapq` can keep ready names in alphabetical order.

**Reread:** d39, *A Common-Sense Guide to DSA*, graphs chapter, topological ordering.

### E4 — Interpret a driver error reply (easy, ~8 min)

**Goal:** Review the error boundary of a driver (software that talks to an instrument), using the same kind of reply as the C++ driver day. SCPI (Standard Commands for Programmable Instruments) uses text commands and replies for instruments.

**Signature:** `def parse_error_reply(reply: str) -> tuple[int, str]`

A reply contains `code,message`. The returned **tuple** is a fixed pair of values, accessed as `result[0]` and `result[1]`. Split at the **first** comma only; later commas belong to the message. Convert the code using Python's `int(code_text)` with its default base. Strip whitespace around the message. If the stripped message starts or ends with a double quote (`"`), require both outer double quotes and at least two characters, remove that pair, then strip whitespace again. Preserve all remaining characters, including internal quotes and commas. Return `(code, message)`.

Raise `ValueError` for a missing comma, a code that `int` cannot convert, an unmatched outer double quote, or a message that is empty after this processing. Error messages are unrestricted. Do not treat a nonzero code as a parsing failure; it describes the instrument error.

**Example:** `parse_error_reply(' -113, "Undefined header, CH2"\r\n')` → `(-113, "Undefined header, CH2")`

**Watch out:** A lone double quote is invalid. This is a small driver reply parser, not a general CSV parser.

**Reread:** d41, learncpp **14.2 Introduction to classes** and *C++ Primer*, chapter 7, classes; revisit the driver's `parseErrorReply` responsibility from d41 E2.

### E5 — Serve the station snapshot (medium, ~11 min)

**Goal:** Build an API (application programming interface) that lets an operator tool read station status. FastAPI connects a **route** (a URL path) to a function. HTTP is the web request/response protocol; `GET` reads a resource. JSON is the text format used for structured response data.

**Signature:** `def create_app(station: str, statuses: dict[str, int]) -> FastAPI`

Return a new FastAPI application on every call. `station` and the instrument IDs are nonempty strings containing letters, digits, hyphens, or underscores. `statuses` maps instrument IDs to valid E2 byte values. Inputs meet these rules; no extra input validation is required. Copy the mapping when creating the app so later caller changes do not affect it. Each app owns its own snapshot (a copy of the status values at creation time).

Start with the supplied `_health_app(station)`, which returns a fresh app with `/health` already implemented. Copy `statuses` and add only the instrument route. The complete route contract is:

- `GET /health`: HTTP status `200`, JSON `{"ok": true, "station": station}`.
- `GET /instruments/{instrument_id}` for a known ID: status `200`, JSON `{"instrument": instrument_id, "flags": decode_status(saved_value)}`. Reuse E2.
- The same instrument route for an unknown ID: status `404` (resource missing), JSON `{"detail": "unknown instrument: ID"}` with the requested ID substituted. Raise FastAPI's `HTTPException` to produce this response.

**Example:** for `create_app("bench-2", {"psu": 9})`, `/instruments/psu` returns `{"instrument": "psu", "flags": {"ready": true, "output_on": false, "overcurrent": true, "overtemperature": false}}`.

**Watch out:** JSON spells Booleans `true`/`false`; Python uses `True`/`False`. FastAPI converts them. Complete E2 first. The tests use `TestClient`, an in-process request client, so do not start a server or use global application state.

**Reread:** d37, FastAPI tutorial **First Steps** (route decorators) and **Testing** (`TestClient`).


### E6 — Count logged ceiling crossings (easy, ~9 min)

**Goal:** Show the operator how often each channel exceeded an alarm ceiling (the highest allowed reading). CSV (comma-separated values) is a text table; its header names the columns. A channel identifies one measured signal. Read the file using `csv.DictReader`, which gives one dictionary per record and handles quoted commas.

**Signature:** `def excursion_counts(path: Path, ceiling: float) -> dict[str, int]`

`Path` represents a file location; a `float` is a number that can have a fractional part. The UTF-8 file has exactly the header `channel,value`, followed by two-field records and possibly completely empty lines. UTF-8 is the encoding used to store text as bytes. Channel names are nonempty; preserve their text exactly, including spaces and case. `ceiling` is finite (neither infinity nor not-a-number). Each value is either finite numeric text accepted by `float()` or invalid numeric text. No header or field-count validation is needed.

Count readings **strictly greater** than `ceiling` under their channel names. Include only channels with at least one crossing. Repeated records count again; equality does not count. Ignore completely empty lines. A header-only file or a file with no crossings returns `{}`; dictionary order does not matter. Let `ValueError` from invalid numeric text and file errors such as `FileNotFoundError` reach the caller; do not return a partial result. Leave the file unchanged.

**Example:** For `channel,value` followed by `rail,5.2`, `rail,5.0`, `rail,5.4`, and `sense,4.0`, a ceiling of `5.0` returns `{"rail": 2}`.

**Watch out:** Open with `encoding="utf-8", newline=""` in a `with` block so the file closes even on error. A quoted name such as `"rail,backup"` is one field; splitting on commas loses it. `counts.get(name, 0)` supplies zero when a name has not been counted yet.

Reread: d04

### E7 — Scan supply currents through a fake transport (easy–medium, ~9 min)

**Goal:** Collect current readings from an operator's channel list. A transport sends commands to an instrument; a fake transport records those calls without hardware. The supplied `Transport` protocol describes the required methods: `write(command)` sends text without a reply; `query(command)` returns reply text. A protocol is an interface an object can match without inheriting from it.

**Signature:** `def scan_current(transport: Transport, channels: list[int]) -> list[float]`

Inputs have the annotated types; channel integers exclude Booleans. Every channel must be 1, 2, or 3. Check the **entire list** first: any invalid channel raises `ValueError` before any transport call, even if it appears after valid channels. Exception message text is unrestricted. An empty list returns `[]` without transport calls.

Then, for each channel in input order, write `f"INST:NSEL {channel}"`, query `"MEAS:CURR?"` exactly once, and append `float(reply)` to the returned list. These SCPI commands select an instrument channel and ask for its current in amperes (A), the unit of electrical current. Keep duplicate channels and measure again each time. Use ordinary `float()` conversion rules, including surrounding whitespace and scientific notation. No extra reply validation is needed.

A write or query exception must reach the caller unchanged; invalid numeric text raises `ValueError`. Stop immediately on any error: no later channel calls, retries, or replacement readings. Do not change the caller's list. This scan only selects and measures; send no other commands and leave the supplied transport open for its owner.

**Example:** With channels `[3, 1, 3]`, replies `"0.2\n"`, `" 1.5e-1 "`, and `"0.25"` produce `[0.2, 0.15, 0.25]`. Calls alternate selection and query: `INST:NSEL 3`, `MEAS:CURR?`, `INST:NSEL 1`, `MEAS:CURR?`, `INST:NSEL 3`, `MEAS:CURR?`.

**Watch out:** Validate in one pass before starting the instrument loop. Checking each channel only just before writing could leave a partly completed scan for an invalid request. The tests provide the fake; you only implement the scan.

Reread: d17
