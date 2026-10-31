# Build a mini chassis tester

**Time:** about 1845 minutes across the plan; daily estimates are below.

A chassis tester is software that connects to instruments and checks a piece of hardware, such as an electronics chassis. Over the 54-day plan you will build `chassis`, a Python package (a folder of related Python modules, each stored in a `.py` file) that does this job in small blocks.

This project follows the work of a test-station software engineer. You will write drivers (code that sends commands to instruments), Themis-style checking (comparing measurements with allowed limits and reporting PASS, FAIL, or ERROR), telemetry (measurements sent over a network), operator tools (commands and a status page for the person running a test), and deployment files (instructions for installing and running the software on a station). Each block adds one part to the same package.

## How to work

Use Bash (the Linux command shell) on Linux or WSL (Windows Subsystem for Linux, which runs Linux on Windows) for your daily loop.

1. On day 4, open a terminal in this `capstone/` folder and run `git init` to make your own repository: a local history of your project. The supplied `pyproject.toml` describes the package and its Python/tool settings; `chassis/__init__.py` marks the package. Keep both. Run `git add .` and `git commit -m "Start chassis tester"` to save your starting point. This repository lives inside the exercises clone; run your project git commands from `capstone/`.
2. Use a branch for each feature. A branch is a separate line of work that you can merge (combine) into your main branch when it works. For example, `git switch -c limit-files` starts one; after committing the finished feature, switch back to your main branch and run `git merge limit-files`. The tracker's branch workflow starts on day 6.
3. Write your code in `chassis/` and your own tests in `tests/` (that is, `capstone/tests/` from the exercises root). A test is a small function that checks an example with `assert`, which raises an error if its condition is false. Use pytest, the test runner installed with the exercises. From this `capstone/` folder, run `../.venv/bin/python -m pytest` on WSL/Linux (or Mac) or `..\.venv\Scripts\python -m pytest` on Windows; your tests can import `from chassis.models import Limit`, for example.
4. Run the supplied gate after each feature and at the end of the block. A gate is a suite of checks for the public interfaces listed below; don't edit `gates/` to make your code pass. Later gates also run all earlier blocks. `Checks: N / M passed` tells you how many individual checks passed. A missing-module error is expected until you create the named files.
5. Commit working changes and report all pass / partial / stuck in the tracker. Keep your own tests as you add later blocks.

Within the first five minutes of each existing slot, run `pwd` to show the current folder and `git status --short` to list changed files from inside `capstone/`. Run the current gate from the exercises root with `bash tools/run.sh b4`, for example. On capstone-only days, run `(cd capstone && ../.venv/bin/python -m pytest)` from the exercises root; `cd` changes folders, `&&` runs the next command only if that succeeds, and parentheses keep the folder change inside that command. After editing, rerun the tests and run `git diff` inside `capstone/` to inspect your changes. This uses the existing task time.

## Block 1 - models and limit files (days 4-6, gate b1 on day 14)

Build small records for instrument measurements and allowed limits, then load those limits from a CSV file. Reject invalid limits with useful file line numbers so an operator can fix the file before a test runs.

### Words you need

- A measurement is one reading, with a name, a numeric value, and a unit such as `V` (volts) or `A` (amps).
- A limit gives a reading's allowed lower and/or upper bound: the smallest and/or largest acceptable value.
- An enum is a named set of choices, such as `Status.PASS`. Its `.value` holds the corresponding string.
- A dataclass is a class whose declared fields generate an initializer and comparison methods. `frozen=True` prevents assigning new values to those fields after construction.
- A type hint such as `name: str` describes the intended type. `float | None` means a number or `None`; here `None` means that bound is absent.
- An exception signals that an operation failed. `ValueError` is Python's built-in exception for an invalid value; your own `LimitFileError` will identify invalid limit files.
- CSV means comma-separated values: a text file with one row per record and a header row naming the columns. Use Python's `csv` module so quoted cells, such as `"supply, main"`, work too.
- A dictionary maps a unique key to a value. Here each key is a limit name and its value is a `Limit` record.
- A signature lists a function's inputs and return type. `os.PathLike` means a path object, such as `pathlib.Path`, that Python can use as a file path.

### Exact interfaces

Create `chassis/models.py` with these names and fields, in this order:

```python
import enum
from dataclasses import dataclass

class Status(enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"

@dataclass(frozen=True)
class Measurement:
    name: str
    value: float
    unit: str

@dataclass(frozen=True)
class Limit:
    name: str
    low: float | None
    high: float | None
    unit: str
```

`Measurement("bus_voltage", 24.1, "V")` stores a reading. `Limit("bus_voltage", 22.0, 30.0, "V")` stores its allowed range. Constructing a `Limit` must raise `ValueError` if both bounds are `None`, either bound is NaN ("not a number", created with `float("nan")`), or both exist and `low > high`. You can detect NaN with `math.isnan` from the standard-library `math` module; comparisons with NaN do not reliably reject it. Equal bounds are valid, and a bound of `0.0` is present, not missing. Put this validation in `Limit.__post_init__`, the method a dataclass calls just after its generated initializer.

Create `chassis/limits.py` with:

```python
class LimitFileError(Exception):
    ...

# Import os, and import Limit from .models.
def load_limits(path: str | os.PathLike[str]) -> dict[str, Limit]:
    ...
```

The `...` marks code you must write. `load_limits` accepts a path string or a path object and returns a dictionary keyed by limit name. The file's header must contain exactly `name,low,high,unit`, in that order. For example:

```csv
# Limits for a bench test
name,low,high,unit
bus_voltage,22.0,30.0,V
supply_current,,3.0,A
chassis_temperature,-20.0,,degC
```

An empty `low` or `high` cell means `None`; otherwise convert it to a number with `float`. A NaN bound is invalid even when the other bound is absent, so reject `rail,nan,,V` and `rail,,nan,V` with `LimitFileError` and the file line number. Strip leading and trailing whitespace from all cells, including the header. Ignore blank lines and lines starting with `#` after leading whitespace. A file containing just a valid header returns an empty dictionary.

Raise `LimitFileError` for a bad header, a row with the wrong number of columns, a non-numeric bound, an empty name, a duplicate name, or a `Limit` whose bounds are invalid. Check duplicates after stripping whitespace. The error message must include the 1-based physical file line number: the first line is 1, and comments and blank lines still count. No exact error wording is required. A file with no header is also invalid; the reference reports line 1 for this case.

### Suggested order

- **Day 4 (~45 minutes): Start your capstone: git init, pyproject.toml, the chassis package.** Follow the setup above, inspect the supplied package files, make your first commit, and write `Status` in `chassis/models.py`. Check that each member's `.value` is the specified string.
- **Day 5 (~50 minutes): Parse limit-file rows: skip blanks and comments, with line-numbered errors.** Use the standard-library `csv` module to read the header and rows. Strip whitespace, convert nonempty bounds with `float`, and check column counts, empty names, and duplicates. Keep physical line numbers even when skipping blanks and `#` comments. Practise with temporary files in your own tests; today you can hold parsed fields in tuples until the records are ready.
- **Day 6 (~55 minutes): Measurement and Limit dataclasses; finish load_limits() returning Limit objects.** Start a feature branch. Add both records and `Limit.__post_init__`, then turn yesterday's parsed fields into a dictionary of `Limit` objects. Wrap invalid bounds in `LimitFileError` with the row's physical line number. Test two bounds, one missing bound, equal bounds, NaN, reversed bounds, and both bounds missing; merge the working feature into your main branch.
- **Day 14 (~10 minutes): Run gate b1 on your capstone.** Save your files, run the gate, and use each failing check's name and message to fix the behavior. The tracker puts this gate on the Sunday review, but run it as soon as your day 6 work is merged: Block 2 starts on day 9 and builds on these records and limits.

Run: Ctrl+Shift+B → Gate: b1

From a terminal at the exercises root: `bash tools/run.sh b1` on WSL/Linux (or Mac), or `tools\run.ps1 b1` on Windows. The gate runs your `chassis` package; your own tests stay in `capstone/tests/`.

## Block 2 - result checking and reports (days 9-15, gate b2 on day 21)

Build a small Themis-style checker that compares your Block 1 measurements with their limits and records PASS, FAIL, or ERROR. Add a JSON report for other software and a short text summary for the operator so a run's outcome is easy to inspect.

### Words you need

- An inclusive bound accepts equality: with a range of 22 to 30 V, both 22 and 30 pass.
- PASS means the reading is within its bounds; FAIL means a valid reading is outside a bound; ERROR means a reading cannot be checked reliably, for example because its unit is wrong or it is missing.
- NaN means "not a number", a special floating-point value you can create with `float("nan")`. Use `math.isnan(value)` to detect it; comparing it with bounds does not reliably reject it.
- An iterable supplies items to a `for` loop. `Iterable[Measurement]` accepts a list or an iterator, which may supply each item only once. Import `Iterable` from `collections.abc`.
- A duplicate measurement repeats a name in the same run. An unexpected measurement has a name with no entry in the limits dictionary.
- Overall status combines all the individual results into one decision. ERROR has priority over FAIL, which has priority over PASS.
- JSON is a text format for dictionaries, lists, strings, numbers, booleans, and `null` (Python's `None`). Use the standard-library `json` module to write it.
- Metadata (`meta`) is extra information about a run, such as `{"station": "bench-1"}`. Keep the caller's dictionary in the report without inventing required keys.
- UTF-8 is the text encoding used for the report file. An indent of 2 means each nested JSON level is moved two spaces to the right; sorted keys means dictionary keys appear in alphabetical order, including inside nested dictionaries.
- Parametrized tests use `@pytest.mark.parametrize` to run one test with several input/expected-output examples. A fixture is a reusable test setup function, such as one providing a temporary file path.
- mypy is a tool that checks type hints without running the program; `--strict` asks it to require and check hints throughout your code.

### Exact interfaces

Keep the Block 1 interfaces working. Create `chassis/themis.py`, importing `dataclass`, `Iterable`, and the Block 1 `Measurement`, `Limit`, and `Status`:

```python
@dataclass(frozen=True)
class CheckResult:
    name: str
    value: float | None
    low: float | None
    high: float | None
    unit: str
    status: Status
    message: str

def check(measurement: Measurement, limit: Limit) -> CheckResult:
    ...

def check_all(
    measurements: Iterable[Measurement], limits: dict[str, Limit]
) -> list[CheckResult]:
    ...

def overall(results: Iterable[CheckResult]) -> Status:
    ...
```

`CheckResult` is a frozen record of a check: the reading's name and value, the applicable bounds, its unit, the decision, and a human-readable message. A value or bound may be `None` as described below. Keep these fields in the order shown.

For `check`, supply a measurement and its corresponding limit. Compare their units and the value:

- Different units produce `Status.ERROR`; the message contains `unit`.
- A NaN measurement value produces `Status.ERROR`.
- A value below `low` or above `high` produces `Status.FAIL`; the message identifies which bound was crossed.
- Otherwise return `Status.PASS`. Bounds are inclusive, and `None` means there is no bound on that side. A bound of zero still applies.

For example, `check(Measurement("bus_voltage", 22.0, "V"), Limit("bus_voltage", 22.0, 30.0, "V"))` passes. At 21.9 V it fails on the low bound, and with unit `mV` it is an error. Exact messages are your choice except for the required phrases.

`check_all` matches readings to limits by name, using the limit dictionary's keys. Return a list ordered by limit name alphabetically first, followed by unexpected measurement names alphabetically. Check matched readings with the same rules as `check`, and handle these run-level problems:

- A limit with no measurement produces ERROR with `not measured` in the message and `value=None`.
- A measurement with no limit produces ERROR with `no limit` in the message, `low=None`, `high=None`, and the measurement's unit.
- A repeated measurement name produces ERROR with `duplicate measurement` in the message for that name. Do not let repeated readings silently become a PASS.

Empty measurements and empty limits produce an empty list. The specification leaves duplicate-result details open: the reference makes one ERROR per duplicated name with `value=None`, and uses that diagnosis even when the name has no limit. The gate checks the duplicate ERROR and phrase without requiring that choice of value or number of duplicate records.

`overall` returns ERROR if any result is ERROR, otherwise FAIL if any is FAIL, otherwise PASS. Empty input returns ERROR: no results cannot establish a passing run.

Create `chassis/report.py` with these functions (import `CheckResult` from `.themis`):

```python
# Import os, and import Any from typing for these type hints.
def write_json_report(
    results: list[CheckResult], path: str | os.PathLike[str], meta: dict[str, Any]
) -> None:
    ...

def summary_text(results: list[CheckResult]) -> str:
    ...
```

`write_json_report` writes UTF-8 JSON to the supplied file path. Turn each `Status` into its string `.value`, keep result-list order, and include all seven result fields. The shape is:

```json
{
  "meta": {"station": "bench-1"},
  "summary": {"total": 1, "pass": 1, "fail": 0, "error": 0, "overall": "PASS"},
  "results": [{"name": "bus_voltage", "value": 24.0, "low": 22.0, "high": 30.0, "unit": "V", "status": "PASS", "message": "within limits"}]
}
```

The output must be strict JSON: NaN and positive or negative infinity in a result's `value`, `low`, or `high` must be written as `null` (Python's `None`). Other field values stay as supplied. You can use `math.isfinite` to detect finite numbers, leaving `None` as `None`. After replacing non-finite numbers, `json.dump(..., allow_nan=False)` can catch any that were missed.

This example shows the fields; your file must use sorted keys and indent 2 (`sort_keys=True, indent=2`). `total` counts all results, the three status counts count their respective results, and `overall` is the string from `overall(results)`. Preserve `meta` as supplied. For an empty list, all counts are zero, `results` is `[]`, and overall is `ERROR`. The writer returns `None`.

`summary_text` returns a string. Its first line is exactly `OVERALL: <STATUS> (<p> pass, <f> fail, <e> error)`, with the overall status and counts filled in. Follow it with one line for each non-PASS result, in input order, formatted `<STATUS> <name>: <message>`. Omit individual PASS lines. For example:

```text
OVERALL: FAIL (1 pass, 1 fail, 0 error)
FAIL supply_current: above high bound 3.0
```

Empty input gives just `OVERALL: ERROR (0 pass, 0 fail, 0 error)`. A final newline is optional.

### Suggested order

- **Day 9 (~40 minutes): Add type hints everywhere and make mypy --strict clean.** Start your Block 2 feature branch. Check your Block 1 functions and fields, then run `../.venv/bin/python -m mypy --strict chassis` from `capstone/` on WSL/Linux (or Mac), or `..\.venv\Scripts\python -m mypy --strict chassis` on Windows. Keep this check clean as you add the new modules.
- **Day 10 (~55 minutes): themis.check() for one measurement against one limit.** Add `CheckResult` and `check`. Write your own pytest tests for a normal reading, both inclusive endpoints, each failure bound, a unit mismatch, and NaN.
- **Day 11 (~55 minutes): check_all() for a whole test with missing and unexpected measurements.** Match names with dictionaries, detect duplicates before overwriting any reading, and sort the two groups of names. Test missing readings, unexpected readings, repeated names, and an iterator as input.
- **Day 12 (~50 minutes): Parametrized tests for themis (every bound and status case).** Group related examples with `pytest.mark.parametrize`. Include one-sided limits, zero bounds, equal bounds, FAIL, and ERROR. Use fixtures in your own tests for shared setup; gate helpers belong to the supplied gate, not your package.
- **Day 13 (~55 minutes): report.write_json_report() and summary_text().** Write sample results to a temporary file, read the JSON back, and check its fields and counts. Test a mix of statuses, empty input, and non-finite result numbers written as `null`. Both reports need the overall decision; write a first version of `overall` now, then finish its coverage in the next capstone task (day 15).
- **Day 15 (~45 minutes): overall(), clean up, mypy clean, merge your Block 2 branch.** Test status priority and empty input, rerun your own tests, and make `mypy --strict chassis` clean. Review names and messages, commit, and merge the working branch into your main branch.
- **Day 21 (~10 minutes): Run gate b2 on your capstone.** Run it as soon as your day 15 work is merged, and fix failing checks before Block 3 starts on day 17. This gate reruns b1 too, so your existing models and limit loader must still work.

Run: Ctrl+Shift+B → Gate: b2

From a terminal at the exercises root: `bash tools/run.sh b2` on WSL/Linux (or Mac), or `tools\run.ps1 b2` on Windows. Your own tests still run separately from `capstone/tests/`.

## Block 3 - instrument drivers (days 17-24, gate b3 on day 28)

Build drivers that control a power supply and read a digital multimeter through VISA, a serial port, or an Ethernet connection. Keep the same driver methods for all three transports. Test the commands without hardware, and make the power supply turn its outputs off whenever its context ends, including after a failed test step.

### Words you need

- SCPI (Standard Commands for Programmable Instruments) is a text command language used by test instruments. A write sends a command such as `OUTP OFF`; a query sends a question such as `*IDN?` and reads a reply.
- A transport is the connection code that sends and receives text. A driver gives those text commands Python method names such as `set_voltage`.
- A protocol describes methods an object must provide, without requiring it to inherit from a particular class. `Transport` lets the same driver use a real connection or a fake.
- VISA is an instrument communication interface; PyVISA is its Python library. A resource name identifies one instrument, for example `GPIB::1::INSTR`. A resource manager opens and owns connections.
- A backend supplies VISA's communication implementation. The backend string `"<path>.yaml@sim"` selects pyvisa-sim, which answers from a YAML text file instead of hardware; YAML stores settings using indented keys and lists.
- A timeout is the longest a read should wait before failing; VISA's `timeout_ms` is in milliseconds (1000 ms is one second), while serial and TCP `timeout` values are in seconds. A termination string marks the end of a command or reply: `"\n"` is a newline.
- A serial port sends bytes over a direct connection, often through a USB adapter. Pyserial opens ports and URL connections; `loop://` echoes each sent byte back for tests. Baud rate is the connection speed, which must match the instrument. ASCII encodes each supported text character as one byte.
- TCP (Transmission Control Protocol) carries an ordered stream of bytes over a network such as Ethernet. A socket is the connection endpoint; a host names the instrument's computer or address and a port selects its service. Raw SCPI commonly uses port 5025. One receive call can contain part of a reply or several replies, so collect bytes through the terminator and save anything beyond it. Tests use `127.0.0.1` (your own computer) with port 0 so the operating system chooses a free server port.
- A power supply (PSU) provides electrical power. Each channel is a separately selected output; volts (`V`) measure voltage, and amps (`A`) measure current. A current limit sets the maximum requested current.
- An envelope is the range of settings a driver permits. Validate inputs before sending even the channel-selection command.
- A digital multimeter (DMM) measures electrical quantities. DC means direct current, whose direction does not alternate; the DC voltage/current queries select that measurement mode.
- An error queue stores instrument errors until software reads them. Draining it means reading repeatedly until the instrument reports code 0, meaning no error.
- A context manager supplies `__enter__` and `__exit__` for a `with` block. Teardown is cleanup performed on exit, even when the body raises an exception. Suppressing an exception means preventing it from reaching the caller.
- A fake transport records commands and returns scripted replies. Supply your own fake as a pytest fixture in your tests; it belongs in your test files, not in `chassis/`.
- A re-export makes a name available from a package's `__init__.py`, so callers can use `from chassis.instruments import PowerSupply`.

### Exact interfaces

Keep Blocks 1 and 2 working. Create `chassis/instruments/base.py` with these public names:

```python
from typing import Protocol

class InstrumentError(Exception):
    code: int
    message: str
    # Construct with InstrumentError(code, message).

class Transport(Protocol):
    def write(self, cmd: str) -> None: ...
    def query(self, cmd: str) -> str: ...
    def close(self) -> None: ...

def parse_error(reply: str) -> tuple[int, str]:
    ...

class VisaTransport:
    def __init__(
        self, resource_name: str, *, backend: str = "", timeout_ms: int = 2000,
        read_termination: str = "\n", write_termination: str = "\n",
    ) -> None: ...
    def write(self, cmd: str) -> None: ...
    def query(self, cmd: str) -> str: ...
    def close(self) -> None: ...
```

The `...` marks code you write. `parse_error('-113,"Undefined header"')` returns `(-113, "Undefined header")`: an integer code and a message with the surrounding quotes removed. Code 0 is valid. A quoted message may contain a comma, so use CSV parsing rather than splitting on every comma. Garbage, such as a missing field or non-integer code, raises `ValueError`.

`VisaTransport` creates its own manager by calling `pyvisa.ResourceManager(backend)` and opens `resource_name` through it. Either `import pyvisa` or `from pyvisa import ResourceManager` is fine. Set the resource's timeout and both termination strings to the supplied values. Forward writes and queries to the resource; `query` strips leading and trailing whitespace from replies. `close` closes the resource first, then releases its manager. Closing one transport must never break another open transport, even with the same backend. PyVISA can return the same manager object for repeated calls, so track how many transports use that object and close it only after the last transport releases it. When PyVISA returns separate managers, close each with its own transport. Implement `__enter__` and `__exit__` so `with VisaTransport(...) as transport:` gives the transport to the body and closes it on exit, including after an exception.

Create `chassis/instruments/serial_transport.py` and `chassis/instruments/tcp_transport.py` with these constructors and the same `write`, `query`, and `close` methods as `Transport`:

```python
class SerialTransport:
    def __init__(
        self, url: str, *, baudrate: int = 9600, timeout: float = 1.0,
        terminator: str = "\n",
    ) -> None: ...
    def write(self, cmd: str) -> None: ...
    def query(self, cmd: str) -> str: ...
    def close(self) -> None: ...

class TcpTransport:
    def __init__(
        self, host: str, port: int, *, timeout: float = 2.0,
        terminator: str = "\n",
    ) -> None: ...
    def write(self, cmd: str) -> None: ...
    def query(self, cmd: str) -> str: ...
    def close(self) -> None: ...
```

`SerialTransport` opens with `serial.serial_for_url(url, baudrate=baudrate, timeout=timeout)`. `write` sends `cmd + terminator` encoded as ASCII. `query` writes the command, reads until the full terminator arrives, and returns the reply with surrounding whitespace stripped. If no complete reply arrives within `timeout`, raise Python's `TimeoutError` with the command text in its message. A partial reply without its terminator also times out. Use `loop://` for tests without a physical port.

`TcpTransport` connects with `socket.create_connection` and sends the same terminated ASCII commands using `sendall`, which sends all the supplied bytes. For `query`, collect bytes across receive calls until a complete terminator arrives. Keep any extra bytes for the next query; sending two replies together must not lose the second. Return stripped text and raise `TimeoutError` naming the command if a complete reply does not arrive in time.

Both transports close their connection with `close()` and implement context managers that close on exit, including when the body raises. They satisfy `Transport`, so `PowerSupply` and `Dmm` below use either without driver changes. For example, an outer `with SerialTransport(url) as transport:` or `with TcpTransport(host, port) as transport:` can own the connection while the inner PSU context shuts down outputs.

Create `chassis/instruments/psu.py`, importing `Transport` from `.base`:

```python
class PowerSupply:
    def __init__(self, transport: Transport, *, channels: int = 3) -> None: ...
    def idn(self) -> str: ...
    def set_voltage(self, ch: int, volts: float) -> None: ...
    def set_current_limit(self, ch: int, amps: float) -> None: ...
    def output(self, ch: int, on: bool) -> None: ...
    def measure_voltage(self, ch: int) -> float: ...
    def check_errors(self) -> None: ...
```

The envelope is channels 1 through 3, voltage 0.0 through 30.0 V, and current 0.0 through 3.0 A. Both endpoints are allowed. Out-of-range input raises `ValueError` **before anything is written**. `channels` gives the number of outputs to shut down; normal use is 1, 2, or 3. The reference also restricts operations to configured channels, but the gate does not add requirements for unconfigured channels or invalid constructor arguments.

Send these commands exactly, in the order shown:

| Method | Transport operations |
| --- | --- |
| `idn()` | query `*IDN?`; return its string |
| `set_voltage(ch, volts)` | write `INST:NSEL {ch}`, then `VOLT {volts:.3f}` |
| `set_current_limit(ch, amps)` | write `INST:NSEL {ch}`, then `CURR {amps:.3f}` |
| `output(ch, on)` | write `INST:NSEL {ch}`, then `OUTP ON` if true or `OUTP OFF` if false |
| `measure_voltage(ch)` | write `INST:NSEL {ch}`, then query `MEAS:VOLT?`; convert the reply to `float` |

Here `{ch}` is the channel number, and `:.3f` formats a number with exactly three decimal places; for example, 12.5 becomes `12.500`.

`PowerSupply` is a context manager. On exit, select each channel from 1 through `channels` and write `OUTP OFF`, even if the body raised. Attempt every channel even if one shutdown fails. If the body succeeded, propagate a teardown error; if the body already raised, suppress teardown errors and preserve the original exception. Never close the transport: its caller owns it. This allows an outer VISA context to close the connection after the PSU has shut down:

```python
with VisaTransport(resource_name) as transport:
    with PowerSupply(transport) as psu:
        psu.set_voltage(1, 5.0)
        psu.output(1, True)
```

Create `chassis/instruments/dmm.py` with:

```python
class Dmm:
    def __init__(self, transport: Transport) -> None: ...
    def idn(self) -> str: ...
    def measure_dc_voltage(self) -> float: ...
    def measure_dc_current(self) -> float: ...
    def check_errors(self) -> None: ...
```

`Dmm.idn()` queries `*IDN?`. `measure_dc_voltage()` queries `MEAS:VOLT:DC?`; `measure_dc_current()` queries `MEAS:CURR:DC?`. Convert each measurement reply to `float`. There is no additional DMM envelope or context-manager requirement.

Both drivers' `check_errors()` query `SYST:ERR?` until code 0, with a maximum of 20 reads per call. Remember the first nonzero code and message, continue draining, then raise `InstrumentError` carrying that first error. Return `None` when the first reply is code 0. If all 20 replies are nonzero, stop and raise the first error rather than reading forever. The specification does not choose a special error code for this case; no new code is required.

Create `chassis/instruments/__init__.py` and re-export `InstrumentError`, `Transport`, `VisaTransport`, `SerialTransport`, `TcpTransport`, `parse_error`, `PowerSupply`, and `Dmm`. The supplied gate uses its own fake transport and `gates/b3/data/instruments.yaml`; its simulated PSU is `GPIB::1::INSTR` and DMM is `GPIB::2::INSTR`. For example, from the exercises root the backend is `"gates/b3/data/instruments.yaml@sim"`. No hardware or internet connection is needed to run the gate after the exercise tools are installed.

### Suggested order

- **Day 17 (~45 minutes): instruments/base.py: InstrumentError, Transport, parse_error().** Start your Block 3 branch. Define the transport methods, add the error's code and message, and test valid error replies and garbage.
- **Day 18 (~55 minutes): VisaTransport over pyvisa, tested against pyvisa-sim.** Open a simulated resource, set timeout and termination strings, then implement forwarding, whitespace stripping, closing, and the context manager. Check that the resource closes before its manager. Open the simulated PSU and DMM together, close either transport, and check that the other still works; finally close the remaining transport and manager.
- **Day 19 (~60 minutes): PowerSupply and Dmm drivers with envelope checks.** Add the public methods and re-exports. Check each command's spelling and order, float conversion, and allowed endpoints. Reject out-of-range values before any transport write.
- **Day 20 (~60 minutes): PSU teardown, check_errors(), and your own FakeTransport tests.** Turn all configured outputs off on context exit and drain error queues with the 20-read cap, preserving the first error. In `capstone/tests/`, make a fake that records writes and queries and scripts several replies per query. Test command order, invalid input with no writes, an exception in the body, a shutdown error, and both together.
- **Day 23 (~50 minutes): SerialTransport over pyserial, tested with loop://.** Open a loop port, send terminated ASCII commands, and read a complete reply with a timeout. Test framing, stripped replies, incomplete replies, closing, and context cleanup. A helper can consume each command's echo on the same port and write a simulated instrument reply so you can reuse both drivers.
- **Day 24 (~55 minutes): TcpTransport for SCPI over Ethernet, plus driver docs.** Connect a TCP socket, use `sendall`, assemble split replies, and keep extra reply bytes for the next query. Test with a local fake server, bounded waits, and joined threads; reuse both drivers unchanged. Write a page per driver in `capstone/docs/` covering commands, allowed inputs, transport choices, failures, and who closes the connection. A failure mode is a way an operation can fail, such as a timeout or failed shutdown. Rerun your tests and `mypy --strict chassis`, then commit and merge.
- **Day 28 (~10 minutes): Run gate b3 on your capstone.** Save your files, run the gate, and fix failing checks. It reruns b1 and b2 as well as the new drivers.

Run: Ctrl+Shift+B → Gate: b3

From a terminal at the exercises root: `bash tools/run.sh b3` on WSL/Linux (or Mac), or `tools\run.ps1 b3` on Windows. Your own tests still run separately from `capstone/tests/`.

## Block 4 - telemetry (days 25-32, gate b4 on day 35)

Build telemetry packets that carry chassis readings over a network, and track sequence numbers to find readings that have not arrived. Add a UDP listener that receives packets in the background, reports damaged packets, and stops cleanly when the test ends.

### Words you need

- A byte holds 8 bits, each a 0 or 1. Binary data stores numbers as bytes rather than text; `bytes` is Python's immutable byte sequence.
- A packet is one structured message. A field is one part of it, and an offset is the number of bytes before a field starts, counting from zero.
- Big-endian means the most significant byte comes first. `u8`, `u16`, `u32`, and `u64` mean unsigned integers stored in 1, 2, 4, and 8 bytes; unsigned means zero or positive. `f32` is a 4-byte floating-point number, which may round a Python `float`.
- A sync word is a fixed number at the beginning that helps identify the packet format. `0xEB90` writes that number in hexadecimal (base 16).
- A sequence number (`seq`) labels each packet in order. A 16-bit sequence wraps from 65535 to 0. A timestamp records a time; `timestamp_us` is an unsigned count of microseconds (one millionth of a second). This format does not specify a starting date for that count.
- A channel is a numbered measurement source. `readings` maps channel numbers to measured values; this packet does not carry names or units.
- A CRC (cyclic redundancy check) is a number calculated from bytes to detect accidental changes. Use `zlib.crc32`; the receiver recalculates it and compares it with the stored number.
- `struct` is Python's standard-library module for converting numbers to and from binary data. Its `>` prefix selects big-endian with no padding; `H`, `Q`, `B`, `f`, and `I` represent `u16`, `u64`, `u8`, `f32`, and `u32`. `pack` makes bytes, and `unpack_from` reads fields at an offset.
- A gap is a skipped sequence number; a duplicate repeats a recently seen number; an out-of-order packet arrives behind the latest forward position. A set stores unique items, making it useful for numbers still missing.
- UDP (User Datagram Protocol) sends separate messages called datagrams. It can lose, repeat, or reorder them. Each datagram here contains exactly one packet.
- A socket is a network endpoint. Binding attaches it to a host address and port, a numbered endpoint on that host. `127.0.0.1` is loopback, which stays on your own computer; port `0` asks the operating system to choose a free port.
- A thread runs work alongside your main code. A background receiver lets the main code continue while waiting for packets. A callback is a function you supply for the receiver to call when something arrives; `Callable[[Packet], None]` means it accepts one `Packet` and returns nothing.
- `threading.Event` lets one thread signal another to stop. A socket timeout limits a receive wait, so the receiver can check that signal. Joining a thread waits for it to finish. `queue.Queue` safely passes items between threads; `get(timeout=...)` lets tests wait for a callback without guessing how long to sleep.

### Exact interfaces

Keep Blocks 1 through 3 working. Create `chassis/telemetry.py` with these names (import `dataclass` from `dataclasses` and `Callable` from `collections.abc`):

```python
class PacketError(Exception):
    ...

@dataclass(frozen=True)
class Packet:
    seq: int
    timestamp_us: int
    readings: dict[int, float]

def build_packet(
    seq: int, timestamp_us: int, readings: dict[int, float]
) -> bytes:
    ...

def parse_packet(data: bytes) -> Packet:
    ...
```

The `...` marks code you write. `Packet` stores the decoded fields in the order shown. Frozen fields cannot be reassigned; the dictionary itself does not need to become immutable.

Use this exact layout, with every multi-byte number in big-endian order and no extra bytes between fields:

| Offset (bytes) | Field | Type and size | Rule |
| --- | --- | --- | --- |
| 0 | `sync` | `u16`, 2 bytes | Always `0xEB90` |
| 2 | `seq` | `u16`, 2 bytes | 0 through 65535 |
| 4 | `timestamp_us` | `u64`, 8 bytes | Unsigned microseconds |
| 12 | `count` | `u8`, 1 byte | Number of readings, 0 through 255 |
| 13 onward | Repeated `channel`, then `value` | `u8` + `f32`, 5 bytes per reading | Channel 0 through 255 |
| `13 + 5 * count` | `crc` | `u32`, 4 bytes | `zlib.crc32` of every preceding byte |

The total length is `17 + 5 * count` bytes. Empty readings are valid: a packet still has its header and CRC. `build_packet` emits channels in ascending numeric order, regardless of dictionary insertion order. Raise `ValueError` for a sequence outside 0 through 65535, more than 255 readings, or any channel outside 0 through 255. Valid timestamps fit the `u64` field; no particular exception is required for timestamps outside it.

`parse_packet` returns a `Packet` with the decoded sequence, timestamp, and channel dictionary. Raise `PacketError` for short data, a bad sync word, length disagreeing with `count` (including extra bytes), a CRC mismatch, or a duplicate channel. Parsing must accept unique channels in any wire order; only the builder must sort. Check length before trying to read missing fields. There is no required error-message wording or priority when several faults are present. Compare non-exact values such as `0.1` using their stored `f32` value or an appropriate tolerance.

Add the sequence tracker in the same module:

```python
class SequenceTracker:
    received: int
    duplicates: int
    out_of_order: int
    missing: set[int]

    def __init__(self) -> None: ...
    def update(self, seq: int) -> list[int]: ...
```

Construct it with no arguments; counters start at zero and `missing` starts empty. The first update returns `[]`. For each later forward packet, return newly skipped numbers in sequence order, wrapping as needed, and add them to `missing`. For example, updates `65533`, then `1` return `[]`, then `[65534, 65535, 0]`. `missing` retains all numbers still absent, rather than just the latest gap.

Recognize direction by the wrapped distance `(seq - last_forward_seq) % 65536`. A distance from 1 through 32767 is forward; a number 1 through 32767 positions behind is late. A duplicate is a number equal to any of the last 1024 seen: return `[]` and increment `duplicates`. Check duplicates before classifying late arrivals. Otherwise a late number increments `out_of_order`, returns `[]`, and removes itself from `missing` if present. A late packet or duplicate does not move the forward position backward. A delayed packet that fills a gap can itself be duplicated later.

The specification leaves some accounting choices open. The reference counts every `update` call in `received`, including duplicates, and remembers the last 1024 arrivals, with duplicate arrivals refreshing history. Exactly 32768 positions apart has no unambiguous direction; the reference treats it as late. The gate checks ordinary received counts, recent duplicates, history expiry on a distinct stream, and direction away from that half-range boundary; it does not require those open choices. Inputs to `update` are valid 16-bit sequence numbers.

Finally add the listener:

```python
class TelemetryListener:
    tracker: SequenceTracker

    def __init__(
        self, host: str, port: int, on_packet: Callable[[Packet], None], *,
        on_error: Callable[[bytes, Exception], None] | None = None,
    ) -> None: ...

    @property
    def port(self) -> int: ...

    def start(self) -> None: ...
    def stop(self) -> None: ...
```

`start` binds a UDP socket to the requested host and port, allowing port 0. After it starts, `port` gives the actual bound port. Start a background thread that receives datagrams with a socket timeout of 0.2 seconds. For each valid packet, parse it, update the public `tracker`, then call `on_packet(packet)` on that thread, including for duplicate and late packets.

For a bad packet, call `on_error(original_bytes, exception)` if supplied, then continue receiving. Without an error callback, continue receiving anyway. Bad packets do not reach the tracker or `on_packet`. Keep callbacks short so the receiving thread can finish its work; callback exceptions and repeated starts are outside this block's contract.

`stop` sets a `threading.Event`, joins the receiver within two seconds, and closes the socket. Implement the context manager so entering starts the listener and exiting stops it, including when the body raises; preserve the body's exception. For example:

```python
from chassis.telemetry import TelemetryListener

with TelemetryListener("127.0.0.1", 0, lambda packet: print(packet.seq)) as listener:
    print(f"Send telemetry to UDP port {listener.port}")
    # Your test or station code does work here while the receiver runs.
```

### Suggested order

- **Day 25 (~30 minutes): Read this brief and sketch the telemetry packet layout by hand.** Start your Block 4 branch. Draw each field's offset, size, and type, including two readings and the CRC; calculate the total length. Practise UDP separately in the day's exercise.
- **Day 26 (~60 minutes): `build_packet()` and `parse_packet()` with full validation.** Spend ~30 minutes starting from your own working d26 packet builder and parser, copying them into `chassis/telemetry.py` and adapting names and return records to `PacketError`, `Packet`, and the interfaces above. Spend ~30 minutes writing your own tests in `capstone/tests/`: use independent byte examples assembled from the layout above, without calling your builder to create parser inputs or expected bytes. Check building and parsing separately, every required rejection, zero readings, and boundary channel numbers.
- **Day 27 (~70 minutes): `SequenceTracker`.** Spend ~30 minutes starting from your own working d27 gap tracker, copying it into `chassis/telemetry.py` and adapting names and any records to the interface above. Spend ~30 minutes writing your own tests in `capstone/tests/`, choosing inputs and expected results independently of that implementation. Cover consecutive numbers, gaps, wraparound, recent duplicates, and delayed arrivals that repair gaps without moving the forward position back. Inspect the returned gaps, public counters, and `missing`, including a duplicate of a delayed repair.
- **Day 29 (~55 minutes): Your own telemetry tests for packets, CRC, and gaps at wraparound.** Keep tests in `capstone/tests/`. Include independently packed bytes so an encoder and decoder with the same bug cannot hide each other's mistake. Change a byte to break the CRC, and give duplicate channels a valid CRC to test that separate check.
- **Day 30 (~50 minutes): Replay a capture through your parser and SequenceTracker.** Save a short capture as fixed packet bytes in a test, including a sequence gap, a duplicate, and a delayed packet. Parse each packet in capture order and pass its sequence to the tracker. Assert decoded readings, counters, and the final missing set; replay needs no socket or listener.
- **Day 32 (~60 minutes): TelemetryListener: UDP thread, Event, timeout, clean stop(), and tests.** Bind to loopback with port 0, receive and parse datagrams, update the tracker, and call `on_packet`. Use a queue with a timeout to observe callbacks. Implement Event-based shutdown and the context manager; test idle shutdown, a body exception, and bad packets followed by a good one, with and without `on_error`. Always stop listeners and join threads in cleanup. Rerun your tests and `mypy --strict chassis`, then commit and merge.
- **Day 35 (~10 minutes): Run gate b4 on your capstone.** Save all files and fix failing checks. This gate runs b1 through b4, so models, limits, checking, reports, and drivers must keep working.

Run: Ctrl+Shift+B → Gate: b4

From a terminal at the exercises root: `bash tools/run.sh b4` on WSL/Linux (or Mac), or `tools\run.ps1 b4` on Windows. The gate uses local UDP only; no instruments or internet are needed. Your own tests still run separately from `capstone/tests/`.

## Block 5 - test executor and operator CLI (days 33-40, gate b5 on day 42)

Build an executor that runs chassis test steps in order and always cleans up the steps it started, even when a reading fails or the operator interrupts the run. Add an operator command that checks saved measurements, prints a summary, and optionally writes the JSON report from Block 2.

### Words you need

- An executor coordinates work: it calls each step's functions, collects readings, and records how the run ended.
- A state is the run's current stage or outcome. A state machine is a set of named states and transitions (moves from one state to another); here a normal run starts IDLE, moves through SETUP and RUNNING, then ends PASS, FAIL, or ERROR. ABORTED means the operator interrupted it and cleanup succeeded.
- Setup prepares a step, for example by enabling a power supply. Teardown cleans it up, for example by disabling that output. Reverse order means the last step started is the first step cleaned up.
- A callable is something you can call like a function. `Callable[[], list[Measurement]]` takes no arguments and returns a list of measurements; `Callable[[], None]` takes no arguments and returns nothing. Store the function itself in `TestStep`, not its return value.
- `KeyboardInterrupt` is the exception Python normally raises for Ctrl+C. It is separate from ordinary `Exception`, so catch it explicitly and still clean up. Return ABORTED only if cleanup succeeds.
- A log is a list of text messages describing what happened. The arrow in `IDLE->SETUP` records a state transition.
- CLI means command-line interface: an operator types a command and options in a terminal. `argparse`, Python's standard-library argument parser, reads those options; `argv` is the list of command words after the program name.
- An exit code is a small integer a process returns to the operating system. A process is a running program; scripts use its exit code to decide whether work succeeded. `main` returns the code; `__main__.py` passes it to `SystemExit` when the process ends.
- stdout is the normal output stream; stderr is the separate stream for diagnostic messages. A traceback is Python's detailed exception listing; input mistakes should produce a short operator message instead.
- CI (continuous integration) runs checks automatically when code is pushed. A PR (pull request) proposes merging a branch and shows the code diff (the changed lines) for review.

### Exact interfaces

Keep Blocks 1 through 4 working. Create `chassis/executor.py`, importing `enum`, `dataclass`, `Callable` from `collections.abc`, your `Measurement` and `Limit`, and Block 2's `CheckResult`:

```python
class RunState(enum.Enum):
    IDLE = "IDLE"
    SETUP = "SETUP"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    ABORTED = "ABORTED"

@dataclass
class TestStep:
    name: str
    run: Callable[[], list[Measurement]]
    setup: Callable[[], None] | None = None
    teardown: Callable[[], None] | None = None

@dataclass
class RunResult:
    state: RunState
    results: list[CheckResult]
    log: list[str]

def run_sequence(steps: list[TestStep], limits: dict[str, Limit]) -> RunResult:
    ...
```

The `...` marks code you write. `RunState` must have the listed member names; the strings shown are a convenient choice of enum values. These two dataclasses do not require `frozen=True`. `TestStep` holds a name, a required reading function, and optional preparation and cleanup functions; `None` means no callback for that phase. `RunResult` holds the final state, checked results, and log.

Run each step's setup and then its run function in list order. Collect all returned measurements into one list and pass that list to `check_all` with the supplied limits; duplicate readings from different steps must still be detected. Use `overall` to choose PASS, FAIL, or ERROR from the checked results. A failed limit check is a result, not a Python exception: collect readings from all steps before deciding the outcome. Empty measurements and empty limits therefore produce ERROR, as in Block 2.

Keep a list of steps whose setup has started. Add the step before calling setup so that partial preparation is cleaned up too; a step with no setup callback still counts as started when execution reaches it. After the forward work ends, call the started steps' teardown callbacks in reverse order, skipping callbacks that are `None`. Do not clean up a step that was never reached. For two successful steps, the order is:

```text
first setup, first run, second setup, second run, second teardown, first teardown
```

The specification also says "setup, then run, then teardown" for each step; its more explicit guarantee puts teardowns **at the end in reverse order**, as shown above. Keep that order on successful runs, errors, and aborts.

- An exception in setup or run ends forward execution immediately: skip the remaining steps and return ERROR after cleanup.
- A `KeyboardInterrupt` in setup or run ends forward execution. Do not re-raise it; return ABORTED if cleanup succeeds.
- Any teardown that raises `Exception` or `KeyboardInterrupt` makes the final state ERROR, overriding PASS, FAIL, ERROR, or ABORTED selected earlier. Do not re-raise these cleanup failures; still attempt every remaining teardown callback.
- Keep state transitions in `log` as `"IDLE->SETUP"`, `"SETUP->RUNNING"`, and similar moves using the enum member names. Also record step events as `"step <name>: <event>"`. Intermediate transitions for multiple steps are not prescribed; make the state history consistent with the final state.
- Record an abort from setup or run as a step event whose `<event>` starts with `abort:`. Record each teardown that raises `Exception` or `KeyboardInterrupt` as a step event whose `<event>` starts with `cleanup failed:`. Use the affected step's name in each record, even when cleanup changes the final state to ERROR. These markers (fixed pieces of text identifying an event) are required exactly as written; any text after them is up to you and may be empty. Other event wording is not prescribed. Keep the checked results from measurements already collected.

After setup or run raises an exception, check the readings collected before it so useful partial results remain available. Choose the final state after all cleanup attempts: a cleanup failure takes priority over an earlier abort or the checked results. An abort followed by failed cleanup therefore returns ERROR, with the abort still recorded in the log.

Create `chassis/cli.py` with:

```python
def main(argv: list[str] | None = None) -> int:
    ...
```

It accepts this command; brackets mark optional arguments and are not typed:

```text
chassis check --limits LIMITS.csv --measurements MEAS.csv [--report OUT.json] [--station NAME]
```

For `main`, pass the words starting with `"check"`, for example `main(["check", "--limits", "limits.csv", "--measurements", "readings.csv"])`. With `argv=None`, read the running program's arguments instead. Use the existing `load_limits` to read the limits. Read measurements using the standard-library `csv` module, with header exactly `name,value,unit` and one measurement per following row:

```csv
name,value,unit
bus_voltage,24.1,V
supply_current,1.2,A
```

Convert each value with `float`, construct `Measurement` records, and pass them to `check_all`. CSV quoting must work for names containing commas. Print `summary_text(results)` to stdout. Return 0 for overall PASS, 1 for FAIL, and 2 for ERROR, including missing measurements, unexpected names, unit mismatch, or NaN; these are valid input files whose readings cannot pass checking. Preserve duplicate rows for `check_all` to diagnose.

A usage mistake (for example a missing required option) or an input-file error returns 3 with a single `error: ...` line on stderr and no traceback. Bad headers, wrong column counts, non-numeric values, unreadable files, and invalid limits are input-file errors. No exact wording after `error: ` is required. The reference also rejects an empty measurement name, strips surrounding cell whitespace, and reports a report-output file error as code 3; the gate does not impose those extra choices. Comment and blank-line handling for measurement files is not specified; it need not match the special limit-file rules.

If `--report` is given, call `write_json_report` even for overall FAIL or ERROR. Use exactly this metadata, keeping the input path strings as passed rather than converting them to absolute paths:

```python
{"station": NAME_or_unknown, "limits": limits_path_string,
 "measurements": measurements_path_string}
```

`NAME_or_unknown` means the `--station` name if supplied, otherwise `"unknown"`. Reuse Block 2's JSON shape, sorted keys, indent 2, and conversion of non-finite result numbers to `null`, including NaN readings reported as ERROR.

Create `chassis/__main__.py` so `python -m chassis check ...` runs `main` and exits with its returned code. The `-m` option runs a package as a program, using its `__main__.py`. From `capstone/`, for example:

```text
python -m chassis check --limits limits.csv --measurements readings.csv --report report.json --station bench-1
```

Use your exercise environment's Python path if `python` does not select it. No additional installed `chassis` executable or packaging entry point is required in this block.

### Suggested order

- **Day 33 (~50 minutes): `executor.py`: `RunState` and `TestStep`.** Start your Block 5 branch. Add the enum and records, including `RunResult`, then sketch the normal state transitions. Write a tiny step that returns a `Measurement` without using hardware.
- **Day 34: No capstone task.** The tracker reserves today for the minimum-ready timed check and notes about your three weakest areas. Use those notes to choose which daily sets to revisit this week.
- **Day 37 (~60 minutes): `run_sequence()` with guaranteed teardown.** First run two successful steps, then add the reverse cleanup list and exception handling. Write your own tests for a failing setup, a failing run, Ctrl+C represented by raising `KeyboardInterrupt`, and a teardown failure that must not prevent other cleanup. Replace 5 minutes of successful-run practice with an abort followed by failed cleanup: check that the final state is ERROR, the abort remains in the log, earlier readings remain in the results, and all remaining cleanup runs. Check the callback order and final state.
- **Day 38 (~60 minutes): Operator CLI: `chassis check` with exit codes 0/1/2/3.** Add `main`, parse the required paths, load both files, reuse checking and text reporting, and return the right integer. Test PASS, FAIL, ERROR, and invalid input separately; capture stdout and stderr with pytest's `capsys` fixture.
- **Day 39 (~55 minutes): `python -m chassis`, JSON report from the CLI, and CLI tests.** Add `__main__.py`, the optional report and station arguments, and metadata. Test paths with spaces, read a generated JSON report back, and use `subprocess.run` with a timeout to check the actual module command and process exit code.
- **Day 40 (~55 minutes): Push to GitHub, add CI (pytest + mypy), open your first PR.** Push your capstone repository and branch, add a GitHub Actions workflow (a file describing automated jobs) that installs the tools and runs `python -m pytest --junitxml=report.xml` and `python -m mypy --strict chassis` from your capstone repository root, then open a PR. The pytest option writes a JUnit XML test report, a structured text file of test outcomes, as practised in d13's JUnit lab. Add an `actions/upload-artifact` step to save `report.xml` as a downloadable artifact (a file retained with the workflow run); set its `path` to `report.xml` and `if: always()` so the report is uploaded even when tests fail. Download it from a workflow run and inspect its test outcomes. Review your diff before merging. From now on, use a PR for each capstone change and require CI to pass; the gate checks program behavior, not your GitHub account or workflow files.
- **Day 42 (~10 minutes): Run gate b5 on your capstone.** Save your files and fix failing checks. This gate reruns b1 through b5, so models, limits, checking, reports, drivers, and telemetry must keep working.

Run: Ctrl+Shift+B → Gate: b5

From a terminal at the exercises root: `bash tools/run.sh b5` on WSL/Linux (or Mac), or `tools\run.ps1 b5` on Windows. Your own tests still run separately from `capstone/tests/`; the gate uses saved CSV files and local processes, with no hardware or internet needed.


## Block 6 - station config, operator status page, and deployment (days 41-50, gate b6 on day 51)

Describe a station's instruments and hardware assignments in a checked configuration file, then expose its current status and latest report to an operator. Add installation and startup instructions as deployment files so another technician can reproduce the station setup.

### Words you need

- Configuration is information you can change without editing program code, such as a station name or instrument address. TOML is a text format for that information; Python's standard-library `tomllib` reads it into dictionaries and lists.
- A TOML table groups named fields under `[station]`. An array of tables, written `[[instruments]]` or `[[uuts]]`, adds one dictionary to a list each time that heading appears.
- An id is a name that uniquely identifies an entry. A reference is another entry's id stored in a field, such as `psu = "psu1"`.
- UUT means unit under test: one piece of hardware being checked. PSU means power supply; DMM means digital multimeter. A PSU channel is one independently controlled output.
- A resource string is the connection address used by VISA, the instrument interface from Block 3. Configuration validation checks assignments without opening those connections.
- Setup order lists which instruments to prepare first. The rule here is a simple sort: all PSUs first, then all DMMs, with ids alphabetical inside each group.
- HTTP is the request/response language used by web clients. An endpoint is a URL path the app answers; GET asks to read data. HTTP status 200 means success; 404 means the requested data is not available.
- FastAPI is the installed Python framework that connects endpoint functions to HTTP requests. `app = FastAPI()` creates the application; `@app.get("/status")` registers a function for that path. An API lets other software read these responses; this block's status page returns JSON, without requiring an HTML design.
- `TestClient` from `fastapi.testclient` calls an app inside your tests, without opening a network port or starting a server. A module-level value lives in the imported module and can be shared by its functions.
- Deployment means installing and starting software on its target machine. systemd is Linux's service manager; a unit file describes how to start a program. A service is a program systemd manages, and `ExecStart` is its startup command.
- Root is Linux's administrator account. A non-root `User` gives this program an ordinary account. Restart policy says when systemd should retry after the program exits. `Type=oneshot` runs a job that finishes after its work; systemd waits for it to exit. `Restart=no` disables automatic retries.
- Docker builds an image, a packaged copy of a program and its tools, using a Dockerfile. A container is a running instance of that image. `FROM` selects the base image, `WORKDIR` sets its working folder, `COPY` adds files, `RUN` installs tools during the build, `USER` selects the runtime account, and `CMD` or `ENTRYPOINT` sets the startup command.
- Ansible applies a list of installation tasks to remote machines. A playbook is a YAML file containing plays; each play selects hosts and tasks. An inventory lists the hosts in named groups. `become: true` allows installation tasks to use administrator privileges.
- An Ansible module performs one task: `copy` transfers a file, `template` transfers a file after filling placeholders, `pip` installs Python packages, `command` runs a command, and `systemd`/`systemd_service` manages a service. `daemon_reload` tells systemd to reread unit files; `enabled` starts it on future boots, and `state: started` starts it now.
- Structural checks read a file's contents without executing its instructions. The gate uses `configparser` (Python's INI-style file reader) for the unit, text lines for Docker, and PyYAML (the installed YAML reader) for Ansible.
- Technical debt is code that makes later changes harder, for example unclear names or repeated logic. A cleanup pass improves that code while keeping its public interfaces working.

### Exact interfaces

Keep Blocks 1 through 5 working. Create `chassis/config.py` with these frozen dataclasses and function signatures; import `dataclass` from `dataclasses` and `os` for path hints:

```python
@dataclass(frozen=True)
class Instrument:
    id: str
    kind: str
    resource: str

@dataclass(frozen=True)
class Uut:
    id: str
    psu: str
    psu_channel: int
    dmm: str

@dataclass(frozen=True)
class StationConfig:
    name: str
    instruments: dict[str, Instrument]
    uuts: dict[str, Uut]

class ConfigError(Exception):
    ...

def load_station_config(path: str | os.PathLike[str]) -> StationConfig:
    ...

def setup_order(config: StationConfig) -> list[str]:
    ...
```

The `...` marks code you write. Keep the field order shown. Frozen records prevent assigning new fields; the dictionaries they contain do not need to be made immutable. `load_station_config` reads TOML using `tomllib` (open the file in binary mode, `"rb"`), then returns records in dictionaries keyed by their ids. Accept a path string or `pathlib.Path`. For example:

```toml
[station]
name = "bench-1"

[[instruments]]
id = "psu1"
kind = "psu"
resource = "TCPIP::10.0.0.5::5025::SOCKET"

[[instruments]]
id = "dmm1"
kind = "dmm"
resource = "TCPIP::10.0.0.6::5025::SOCKET"

[[uuts]]
id = "uut1"
psu = "psu1"
psu_channel = 1
dmm = "dmm1"
```

Here `config.name` is `"bench-1"`, `config.instruments["psu1"]` is its `Instrument`, and `config.uuts["uut1"]` is its `Uut`. Reject these problems by raising `ConfigError`:

- A missing station name, including an absent station table, absent name field, or empty name.
- Duplicate instrument ids, duplicate resource strings (even across different kinds), or an unknown kind. The allowed kinds are exactly `"psu"` and `"dmm"`.
- A duplicate UUT id.
- A UUT's `psu` or `dmm` referring to an unknown instrument, or to an instrument of the wrong kind. The PSU reference must identify a `"psu"`; the DMM reference must identify a `"dmm"`.
- A `psu_channel` outside 1 through 3; all three channels are valid.
- Two UUTs sharing the same `(psu, psu_channel)` pair.

Different channels on one PSU are allowed. The same channel number on different PSUs is allowed, and multiple UUTs may share a DMM. A named station may have no instruments or UUTs; absent lists can be treated as empty. Check duplicates before inserting a record into a dictionary so an earlier entry is not silently overwritten. Exact error messages are your choice. The reference also rejects wrongly typed or missing record fields and wraps unreadable files and invalid TOML in `ConfigError`; those extra error policies are not gate requirements.

`setup_order` returns all instrument ids, including instruments unused by a UUT. Put PSUs before DMMs and sort ids alphabetically within each kind. For example, a station containing `a_dmm`, `z_psu`, `z_dmm`, and `b_psu` returns `["b_psu", "z_psu", "a_dmm", "z_dmm"]`. An empty station returns `[]`. This fixed rule needs no general graph algorithm.

Create `chassis/web.py` with these public names:

```python
# Import FastAPI from fastapi, and Any from typing.
app = FastAPI()

def set_status(station: str, state: str) -> None:
    ...

def set_latest_report(report: dict[str, Any]) -> None:
    ...
```

Register two GET endpoints on `app`:

- `/status` returns exactly `{"station": str, "state": str}` as JSON, initially `{"station": "unknown", "state": "IDLE"}`. `set_status` replaces both values; the next GET must show them. Supply strings such as `"RUNNING"` or `"FAIL"`; no state enum conversion is required.
- `/results/latest` returns the last report dictionary passed to `set_latest_report`. Before any report is registered, return HTTP 404; FastAPI's `HTTPException` can do this. Preserve the report's contents, including nested lists and dictionaries. A later call replaces the earlier report, and an empty dictionary is still a registered report, not a missing one.

Reuse Block 2's JSON report shape when publishing a test report. A report loaded from the strict JSON file written by `write_json_report` already contains `null` for non-finite result numbers; `/results/latest` must preserve those values. The specification does not require validation of that shape, copying the caller's dictionary, persistence across restarts, particular 404 text, or automatic connection to the CLI/executor. These setters and the app share state within one process. Write your own tests with `with TestClient(app) as client:` and `client.get("/status")`; no live server is required for this block.

Add these deployment files, relative to `capstone/`:

- `deploy/chassis-telemetry.service`: an INI-style systemd unit with `[Unit]`, `[Service]`, and `[Install]` sections. `[Unit]` needs a `Description`, `After=network-online.target`, and `Wants=network-online.target`. `[Service]` needs `Type=oneshot`, an `ExecStart` running `python -m chassis check` with the saved-file arguments from Block 5, `Restart=no`, and a non-root `User=`. `[Install]` needs `WantedBy=multi-user.target`. Additional dependencies are allowed, on the same line or in repeated `After`, `Wants`, or `WantedBy` lines. Use a real account and paths appropriate to your example station.
- `Dockerfile`: use `FROM python:3.12-slim` (another Python 3.12 slim tag is fine), a `WORKDIR`, a `COPY` of the project, a `RUN` using `pip install`, and `CMD` or `ENTRYPOINT` invoking `python -m chassis`. `python -m pip install` is also valid. Include a `USER` line selecting a non-root runtime account. Either shell commands or JSON argument lists can express the startup command.
- `deploy/ansible/playbook.yml`: write exactly one play with `hosts: test_stations` and `become: true`. Include tasks using `ansible.builtin.copy` or `ansible.builtin.template` to install `chassis-telemetry.service`: set `dest` to the unit file (for example `/etc/systemd/system/chassis-telemetry.service`), or to a directory ending in `/` with `src` naming `chassis-telemetry.service`. Copying only the project folder does not satisfy unit installation. The copy/template arguments may be a YAML mapping, `key=value` text, or task-level `args`. Include `ansible.builtin.pip` or `ansible.builtin.command` for installation. Tasks may be nested inside `block`, `rescue`, or `always` lists; a block groups tasks, while rescue and always list error-handling and cleanup tasks. A task using `ansible.builtin.systemd` or `ansible.builtin.systemd_service` must set `enabled: true`, `state: started`, and `daemon_reload: true`.
- `deploy/ansible/inventory.ini`: include a `[test_stations]` group with at least one host. Example addresses can be placeholders; document what the technician must change.

The gate reads these files; it never runs Docker, systemd, or Ansible. Despite the required unit filename, there is no specified telemetry subcommand: run the existing `check` command with saved input files. That command finishes after one check: PASS exits 0, a UUT FAIL exits 1, and a checking ERROR exits 2. A UUT FAIL is a valid test outcome; restarting on that exit would re-check the same saved files forever. Use `Type=oneshot` with `Restart=no`, so each explicit start checks the files once. No `RestartSec` delay is needed because automatic retries are disabled. `Restart=on-failure` belongs on a long-running service such as the status web app, where an unexpected exit should restart the process; running that app as a service is beyond this block. No particular directory layout on the target or account name is required.

### Suggested order

- **Day 41 (~60 minutes): `config.py`: station config in TOML, validated.** Start your Block 6 branch and PR. Add the records, load a small station file, and check the required errors. Keep error messages useful to an operator. Write your own tests in `capstone/tests/` using temporary files.
- **Day 43 (~50 minutes): `web.py`: `/status` and `/results/latest`.** Add the app, setters, and endpoints. Test default status, updated status, missing report, and replacing a report with `TestClient`. Read a Block 2 JSON report into a dictionary and publish it to check that the modules fit together.
- **Day 45 (~55 minutes): systemd unit, Dockerfile, Ansible playbook and inventory.** Spend ~47 minutes writing the four files above. Choose the account, install folder, and startup command consistently. Check the unit sections, Docker instructions, and YAML indentation. Spend ~8 minutes running the startup check command directly with saved measurements that produce PASS, FAIL, and ERROR. Compare the exit codes with 0, 1, and 2, then explain why FAIL must not trigger a retry of the same files. Use the Python path for your local environment; running a container or deploying to a real station is not needed for the gate.
- **Day 46 (~50 minutes): `setup_order()` and config tests for shared channels and wrong kinds.** Implement the fixed two-group sort. Test scrambled input order, unused instruments, an empty station, each invalid reference, and a shared PSU channel. Also show that separate channels and sharing a DMM are valid.
- **Day 48 (~45 minutes): Technical-debt pass: names, duplicated code, interfaces.** Make small cleanup commits in one PR, review the diff, and keep CI green. Reuse existing checking and reporting functions, preserve the listed public names, and run your own pytest tests and `mypy --strict chassis`.
- **Day 50 (~45 minutes): Operator README: install, configure, run, read the report.** Write instructions in your capstone repository for a technician. Give the Python/tool installation steps, a sample TOML configuration, the exact saved-file check command, report location, exit codes, and the meaning of PASS/FAIL/ERROR. Explain which deployment addresses and paths to edit, and that the status API needs the app and publication calls in the same process. Walk through the instructions from a fresh terminal.
- **Day 51 (~10 minutes): Run gate b6 on your capstone.** Save your files and fix failing checks. This gate reruns b1 through b6, so every earlier interface must still work. Finish the PR after your tests, type checks, CI, and gate pass.

Run: Ctrl+Shift+B → Gate: b6

From a terminal at the exercises root: `bash tools/run.sh b6` on WSL/Linux (or Mac), or `tools\run.ps1 b6` on Windows. Your own tests still run separately from `capstone/tests/`; no hardware, internet, Linux service manager, or Docker installation is needed for the gate.

## Final repairs, demonstration, and gates (days 52-53)

- [ ] **Day 52 (~50 minutes): Run every gate; fix anything red.** Run cumulative gate b6 using the command above; it reruns b1 through b6. Fix failing behavior, rerun your own tests and `mypy --strict chassis`, and report all pass / partial / stuck in the tracker.
- [ ] **Day 53 (~45 minutes): Prepare a five-minute demo script of your mini chassis tester.** Write and rehearse a short walkthrough using your existing modules, with no real hardware required. Cover each item below:
  - Load a CSV limits file with `load_limits`.
  - Drive a simulated PSU and DMM using the Block 3 drivers and pyvisa-sim; set a PSU output and read measurements.
  - Check the readings against the loaded limits and explain PASS, FAIL, and ERROR.
  - Print the text summary, write a JSON report, and show where the operator finds the results.
  - Show telemetry gaps with `SequenceTracker`: for example, sequences 10 then 12 report 11 as missing. Explain what that missing packet means.
- [ ] **Day 53 (~15 minutes): Final gate run: every gate green.** Run cumulative gate b6 again after your last changes, confirm every check passes, and report all pass / partial / stuck in the tracker.

The demonstration is a manual task: b6 checks the interfaces above, but does not assess your presentation or require a particular demo filename or script layout.
