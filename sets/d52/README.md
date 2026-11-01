# d52 — Find your way in code you didn't write

**Time:** about 45 minutes · **Read first:** the code-reading primer below and the supplied package's tests · **You edit:** `starter/map_answers.py`, `starter/legacy_station/load.py`, one existing package helper you locate, and a new `starter/legacy_station/tests/test_regression.py`.

## What you're building

On your first day, a chassis test station already has working instrument drivers (software that translates Python requests into equipment commands) and reports. Your job is to understand one path through that code, add an instrument using its existing pattern, and repair a technician's reported defect. All equipment is replaced by in-memory objects; you need no bench hardware.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in the E1 answer file and E2 driver. E3 asks you to locate and repair existing code and add a test. Keep the supplied code otherwise intact. Don't edit the set's top-level `tests/`, or the existing files under `starter/legacy_station/tests/`; add your regression test (a check that prevents a repaired defect from returning) there.
2. Press **Ctrl+Shift+B → Test: d52** (or run `bash tools/run.sh d52` / `tools\run.ps1 d52` from the repository root). At first you'll see `Exercises: 0 / 3 passed`. Rerun after each exercise. Until your regression file exists, E3 reports `NotImplementedError` with the required path.
3. Report **all pass / partial / stuck** in the tracker.

### How to read an unfamiliar codebase

A **module** is one Python file. A **package** groups modules in a directory with an `__init__.py` file. **Legacy code** is existing code you inherit responsibility for. An **entry point** is the function callers use to start an operation; here, start reading at `run_station` in `runner.py`.

Follow one **call path**, the sequence of functions that call each other: pick a single step, follow its measurement request into a driver, then follow the result back to its report row. Read the tests next: they show the behavior callers already rely on. Search for a name instead of reading every file in order. In Linux or Git Bash, `grep -rn "run_station" starter/legacy_station` searches recursively (`-r`) and prints line numbers (`-n`). In an editor, use Find in Files for the same name. Keep changes small and rerun the tests after each change.

A **driver** translates Python method calls into instrument commands. A **method** is a function attached to an object. A **transport** sends commands and receives replies; a **fake** replaces it with predictable in-memory behavior. A **timeout** limits how long a transport may wait. A **query** sends a command and requests a reply. These drivers pass a timeout in seconds to every transport call; the fake records it without waiting. A real transport enforces the deadline and raises `TimeoutError` on silence.

A **class** describes a kind of object and its methods. A **base class** (also called a superclass) provides shared methods; a **subclass** inherits them and supplies specialized behavior. **Inherited** means supplied by the base class without redefining it. An **abstract method** requires a subclass implementation before instances can be created. An **interface** is the set of methods callers use. A **protocol** describes methods an object must provide; here `Transport` requires `write` and `query`. The leading underscore in `_query` marks an internal helper, which a driver subclass may reuse.

An **initializer** (`__init__`) sets up a newly created object. A **dataclass** supplies an initializer and named fields: `Step` describes one check and `Result` holds one report row. A **dictionary** maps labels to values; the runner's driver dictionary selects an instrument by label. A **list** preserves order. `dict[str, Driver]` means string labels mapped to driver objects. To practice following transformations, this unrelated operator-label example makes a new list:

```python
labels = ["bench-a", "bench-b"]
normalized = [label.upper() for label in labels]
print(normalized)  # ['BENCH-A', 'BENCH-B']
```

The package deliberately has a long function, a **magic number** (an unexplained numeric setting), a duplicated helper, and a **module-level global** (shared state stored outside functions). These are **code smells**, clues that maintenance might be harder, rather than proof of a defect. Leave them alone for this task; fix only the reported behavior.

### Run the existing package

From the repository root, use `.venv/bin/python -m pytest sets/d52/starter/legacy_station/tests -q` in WSL or Codespaces to run the package's own tests (native Windows PowerShell: replace `.venv/bin/python` with `.venv\Scripts\python`). They already pass before you begin. **pytest** discovers functions whose names start with `test_`; an `assert` states a condition that must be true. Those old checks protect existing behavior, but they do not cover every possible input.

For interactive exploration, change directory to `sets/d52`, then start Python with `../../.venv/bin/python` in WSL or Codespaces (native Windows PowerShell: `..\..\.venv\Scripts\python`) so `starter` can be imported. At the Python prompt, try:

```python
from starter.legacy_station.meter import VoltageMeter
from starter.legacy_station.runner import Step, run_station
from starter.legacy_station.tests.fakes import FakeTransport
meter = VoltageMeter(FakeTransport({"MEAS:VOLT?": "5"}))
rows = run_station({"meter": meter}, [Step("rail", "meter", 4, 6)])
[(row.name, row.value, row.status) for row in rows]  # [('rail', 5.0, 'PASS')]
```

`FakeTransport(replies)` accepts a dictionary of exact query commands and their text replies. Its `writes` and `queries` lists record `(command, timeout_s)` pairs. A missing reply entry raises `KeyError`. The runner validates its whole plan before reading, averages each step's requested readings, and preserves step order. An **exception** interrupts normal execution. The runner catches instrument exceptions, produces an `ERROR` row, and continues with later steps. Instrument setup and shutdown belong to the caller.

## Exercises

### E1 — Map it (easy, ~10 min)

**Goal:** Find the owners of three responsibilities by tracing the supplied code.

**Signature:** `def map_answers() -> dict[str, str]`

**Contract:** Return a dictionary with exactly `"Q1"`, `"Q2"`, and `"Q3"`. Each value is your chosen uppercase option letter (`"A"`, `"B"`, or `"C"`). Return letters, not module names or option text. The failure messages give a reading hint without revealing the answer.

**Example:** `sorted(map_answers())` → `["Q1", "Q2", "Q3"]`; `sorted` returns dictionary keys in order.

**Q1.** Which method forwards the driver's stored timeout to the transport for each measurement query?

- A. `runner.run_station`
- B. `base.Driver._query`
- C. `meter._number`

<details>
<summary>Why it matters on the job</summary>

Find the common query path before changing how instruments communicate.
</details>

**Q2.** Which function compares the numeric reading with the configured acceptance limits, supplying the decision the runner labels PASS or FAIL?

- A. `base.Driver.identify`
- B. `supply.PowerSupply.enable`
- C. `limits.check_limits`

<details>
<summary>Why it matters on the job</summary>

A report formatting change cannot repair a wrong numerical comparison.
</details>

**Q3.** Which class must a new station instrument subclass so the existing shared interface is retained?

- A. `base.Driver`
- B. `runner.Step`
- C. `tests.fakes.FakeTransport`

<details>
<summary>Why it matters on the job</summary>

Following the existing interface lets the generic runner use another instrument.
</details>

**Watch out:** The transport enforces actual waiting; the driver supplies its timeout. A fake records the argument without measuring elapsed time.

**Reread:** The primer's entry-point, call-path, and base-class paragraphs; the existing class declarations and measurement path.

### E2 — Add a feature without breaking anything (medium, ~20 min)

**Goal:** Complete `ElectronicLoad` in `starter/legacy_station/load.py` by following the supplied drivers. An **electronic load** draws a controlled current from a power supply. **A** means amperes, the unit of current; **V** means volts, the unit of voltage. This invented instrument uses text commands with no trailing newline.

**Signature:** `ElectronicLoad(transport: Transport, timeout_s: float = 0.4)` (inherited initializer), with these methods:

```python
def set_current(self, current_a: float) -> None
def enable(self, enabled: bool) -> None
def read(self) -> float
```

**Contract:** Keep the supplied superclass and inherited initializer, identification, and timeout behavior. Use the shared write/query helpers. Every successful operation sends exactly one command; propagate the original transport exception unchanged, with no retries (repeated attempts).

- `set_current`: accept a finite float in `0 <= current_a <= 10`. **Finite** excludes infinity and NaN (a special "not a number" value); `math.isfinite` checks this. Otherwise raise `ValueError` before communicating. Send `CURR ` followed by the value formatted to exactly three decimal places using `f"{current_a:.3f}"`. Return `None`; do not enable the input or query a readback.
- `enable`: its input is already a bool (`True` or `False`). Send exactly `INPUT ON` for `True`, otherwise `INPUT OFF`. Return `None`; do not change the programmed current.
- `read`: query exactly `MEAS:CURR?`. Strip surrounding whitespace, convert the bare reply with `float()`, and return it unchanged in amperes. Raise `ValueError` for invalid or nonfinite replies. Do not round, clamp (force into a range), or add a unit suffix; a finite negative diagnostic reading is valid.

**Example:** With fake reply `" 1.25\n"` and timeout `0.75`, `set_current(1.5)` then `enable(True)` record writes `[("CURR 1.500", 0.75), ("INPUT ON", 0.75)]`. `read()` returns `1.25` and records query `("MEAS:CURR?", 0.75)`.

**Watch out:** Use the existing pattern instead of changing the runner or transport. No registration table needs updating: a caller passes `{"load": load}` as its drivers dictionary. The grader checks the fake's command history and reruns the package's old tests. The E2 checks use interior readings so E3 can be completed independently.

**Reread:** The two existing instrument modules and the shared communication helpers.

### E3 — Leave it a bit better (medium, ~15 min)

**Goal:** Find and repair one shared defect, then add a **regression test**, a check that prevents this same defect from returning.

**Technician's bug report:** "The rail has limits 4.750 through 5.250 V. A reading of exactly 4.750 V or exactly 5.250 V shows FAIL, but the approved procedure says both endpoints are acceptable. Values inside the band work. Please fix the shared comparison so every instrument benefits."

**Contract:** Locate the common numerical comparison helper and change its rule to `low <= value <= high`, with no rounding or tolerance added. Equal lower and upper bounds form a valid one-value band. Preserve its existing validation: a nonfinite reading, nonfinite bound, or reversed bounds must raise `ValueError`. Keep all other package behavior and all existing tests intact. Do not change limits at a caller or special-case the rail name.

Create `starter/legacy_station/tests/test_regression.py` with at least one pytest function named `test_e3_<description>`. Use the package's public comparison helper or the runner to assert that an exact endpoint passes; testing both ends is encouraged. Import via `starter.legacy_station...`. The file must run on its own with the supplied package, stdlib (Python's built-in library), and pytest; do not depend on the grader or its fixtures (helper values pytest supplies to test functions). The provided `FakeTransport` is available if you exercise the runner. Do not skip the test or detect which version is running.

The grader runs your new test with the repaired code, then against a **mutant**, a copy whose comparison module is restored to the original supplied code. Your test must pass on the repair and fail with an assertion on the original; an import error or unrelated exception does not count. It also reruns the old package tests with your repair. Only the comparison module is replaced for this check.

**Example:** After repair, comparing `4.75` and `5.25` separately against the band `[4.75, 5.25]` returns `True` for each.

**Watch out:** Merely adding the regression file does not demonstrate the bug is fixed. First run it against the old code and see the assertion fail, make the small repair, then run the full package suite. You add one file under the package's own tests; the set's top-level grader stays untouched.

**Reread:** The technician report, the runner's numerical call path, and the existing tests' assertion style.
