# d10 — Fixtures: fake instruments for tests

**Time:** about 45 minutes · **Read first:** [pytest: How to use fixtures (including tmp_path)](https://docs.pytest.org/en/stable/how-to/fixtures.html) and [Missing Semester: Shell Tools and Scripting](https://missing.csail.mit.edu/2020/shell-tools/) (second half: find, grep, history) · **You edit:** `starter/fixtures_learner.py`

## What you're building

A test station needs repeatable tests without a physical power supply attached. You'll provide fake instruments, temporary limit files, safe output cleanup, and measurement builders that tests can request by name. A **fake** is a small substitute for real equipment whose behavior you control.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/fixtures_learner.py`. Keep the supplied imports, types, signatures, and `@pytest.fixture` decorators. Don't edit `tests/`, `conftest.py`, or the provided `starter/fakes.py`.
2. Press **Ctrl+Shift+B → Test: d10** (or run `bash tools/run.sh d10` / `tools\run.ps1 d10` from the repository root). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **fixture** is a function that pytest runs to supply a test's named argument. A **decorator**, here `@pytest.fixture`, marks a function for pytest. A **dependency** is another fixture requested as an argument; pytest supplies it automatically. The supplied set-root `conftest.py` registers your fixtures so the tests can request them. Tests request fixture names; they do not call decorated fixture functions directly.

**Scope** controls how long pytest reuses a fixture result. The default, **function scope**, gives each test a new result; two requests within the same test share that result. Module scope shares one result across a test file; session scope shares it across the entire test run. Keep all four fixtures function-scoped so command history cannot leak between tests.

**Setup** runs before a test. **Teardown** runs afterward, including after a failed **assertion** (a condition a test requires to be true). A **yield fixture** pauses at `yield`, hands a value to the test, and resumes for teardown. `try/finally` places cleanup in a block that runs when leaving the `try` block. `Iterator[FakeInstrument]` describes a fixture that yields a fake instrument.

Here is another station fixture showing the lifecycle. The `with` block closes its file when control leaves the block:

```python
@pytest.fixture
def station_log(tmp_path):
    path = tmp_path / "station.log"
    with path.open("w", encoding="utf-8") as log:
        yield log  # The with block closes the file during teardown.
```

A **Path** is a `pathlib` object representing a filesystem path. `tmp_path` is pytest's built-in fixture providing a separate temporary directory for each test; use `/` to join a directory and filename. `path.write_text(text, encoding="utf-8")` writes text and closes the file. Never use a fixed absolute path for test files.

A **factory** is a function that creates a new object on each call. Here one fixture returns a function, and the test calls that function many times. `Callable[..., Reading]` means a callable returning a `Reading`; the dots leave argument details to the contract below. `Reading` is a supplied **TypedDict**, a type description for an ordinary dictionary with specified keys and value types.

For the shell reading, **find** searches directory trees, **grep** searches text, and **history** recalls shell commands. On Linux, practice finding `test_d10.py`, searching for `OUTP`, and recalling your test command. These are optional navigation drills; the graded exercises run on Windows and Linux without a shell dependency.

## Exercises

### E1 — Supply a fresh fake power supply (easy, ~8 min)

**Goal:** Give each station test its own **PSU** (power supply unit), with repeatable responses to two instrument commands.

**Signature:** `def fake_psu() -> FakeInstrument` (fixture).

Return a new provided `FakeInstrument` constructed with this dictionary of command-to-reply strings:

| Command | Exact reply |
| --- | --- |
| `*IDN?` | `ACME,PSU-28,SIM001,1.0` |
| `MEAS:VOLT?` | `28.0` |

These are **SCPI** (Standard Commands for Programmable Instruments) commands: `*IDN?` asks for identification, and `MEAS:VOLT?` asks for voltage. The replies are scripted, meaning fixed in advance. `FakeInstrument(replies)` copies the dictionary; `.query(command)` returns its reply without consuming it and raises `KeyError` for an unknown command. `.write(command)` appends to the public `.writes` list; queries do not append. No command touches hardware.

**Example:** a test requesting `fake_psu` can call `fake_psu.query("MEAS:VOLT?")` → `"28.0"`. Its initial `fake_psu.writes` is `[]`.

**Watch out:** Return the object, not the class. Keep the default function scope and construct a fresh instance inside the fixture. E3 depends on E1.

**Reread:** pytest, “Requesting fixtures,” “Fixtures are reusable,” and “Scope: sharing fixtures across classes, modules, packages or session.”

### E2 — Create a temporary limits file (easy, ~9 min)

**Goal:** Give a station test a private limits file. A **limit** is an allowed measurement boundary; **CSV** means comma-separated values, a text table with a header and one row per record.

**Signature:** `def limits_file(tmp_path: Path) -> Path` (fixture).

Write `limits.csv` directly inside `tmp_path`, using UTF-8 (a standard encoding that maps text to bytes). Return its `Path`, after the file is written and closed. Its parsed header and rows must be exactly these, in this order; Windows and Linux line endings both work:

```csv
name,low,high,unit
bus_voltage,27.0,29.0,V
supply_current,0.0,2.0,A
```

`name` identifies the measurement; `low` and `high` are its lower and upper boundaries; `unit` is its measurement unit (`V` = volts, `A` = amperes). You are writing a test input, not evaluating limits.

**Example:** when pytest supplies a temporary directory `folder`, the result is `folder / "limits.csv"` containing the table above.

**Watch out:** Return a `Path`, not a string or file handle. Request `tmp_path` by argument name. Pytest manages the temporary directory; no manual deletion is needed.

**Reread:** pytest, “Requesting fixtures” and “Fixtures can request other fixtures”; follow its `tmp_path` link to “The tmp_path fixture.”

### E3 — Always switch the output off (medium, ~16 min)

**Goal:** Model a station step that enables a supply, lets the test run, then disables it even when an assertion fails.

**Signature:** `def powered_psu(fake_psu: FakeInstrument) -> Iterator[FakeInstrument]` (yield fixture).

Write `"OUTP ON"` to the supplied `fake_psu` before yielding that exact object. `OUTP` means output: ON enables it and OFF disables it. Yield once, inside a `try` block, and write `"OUTP OFF"` in `finally` after the test finishes. Do not catch or suppress test failures. Do not create another fake or clear its command history.

**Example:** if a test writes `"MEAS:START"` (a sample station command), the history after teardown is `["OUTP ON", "MEAS:START", "OUTP OFF"]` for both passing and failing tests. During the test, the final OFF has not happened yet.

**Watch out:** `return` would end the fixture without the teardown lifecycle. The checks launch tiny nested pytest runs, including an intentionally failing test; your outer check passes only when cleanup was recorded afterward. This does not require you to write or run a deliberately failing test yourself.

**Reread:** pytest, “Teardown/Cleanup (AKA Fixture finalization),” “yield fixtures (recommended),” and “Safe teardowns.”

### E4 — Build independent measurement dictionaries (medium, ~12 min)

**Goal:** Give tests a convenient factory for station readings. A **reading** is one measured value with its name and unit.

**Signature:** `def make_reading() -> Callable[..., Reading]` (fixture). Return a function with the signature `def build_reading(name: str = "bus_voltage", value: float = 28.0, unit: str = "V") -> Reading`.

Each call to that returned function creates a new dictionary with exactly the keys `"name"`, `"value"`, and `"unit"`. Use the corresponding argument values unchanged. All arguments are optional and support positional or keyword calls; omitted arguments use the displayed defaults. Accept empty strings, zero, and negative values; no validation or conversion is required.

**Example:** a test requesting `make_reading` calls `make_reading(value=27.5)` → `{"name": "bus_voltage", "value": 27.5, "unit": "V"}`. Calling it twice produces separate dictionaries, so editing one cannot change another or any later default.

**Watch out:** Return the inner function itself, without calling it. The fixture returns a factory; the factory returns a dictionary.

**Reread:** pytest, “Factories as fixtures.” For navigating these checks, revisit Missing Semester, “Finding files,” “Finding code,” and “Finding shell commands.”
