# d11 — Parametrize and markers: one test, many cases

**Time:** about 45 minutes · **Read first:** pytest [How to parametrize fixtures and test functions](https://docs.pytest.org/en/stable/how-to/parametrize.html), pytest [How to mark test functions](https://docs.pytest.org/en/stable/how-to/mark.html), and Missing Semester [Data Wrangling](https://missing.csail.mit.edu/2020/data-wrangling/) · **You edit:** `starter/test_scpi_learner.py`

## What you're building

A chassis test station needs to read voltages and instrument error messages in several formats. You will write tests for a supplied SCPI driver, the small module that translates station requests and instrument replies. A module is a Python file. SCPI means *Standard Commands for Programmable Instruments*, a text command language used by lab equipment. pytest is the Python tool that discovers and runs your tests.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/test_scpi_learner.py` and add the decorators requested below. Keep the four function names, parameter names, and type hints (the annotations after ?:? and ?->? that describe input and output types). Don't edit `scpi.py`, `pytest.ini`, or `tests/`.
2. Press **Ctrl+Shift+B → Test: d11** (or run `bash tools/run.sh d11` / `tools\run.ps1 d11`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **parameter** is a named function input. **Parametrization** makes pytest run one test function for each row of inputs. A **decorator** is an `@...` line above a function that adds instructions to it. This station-status example is separate from your voltage tests:

```python
@pytest.mark.parametrize("status", ["READY", "BUSY"])
def test_station_status(status: str) -> None:
    assert status in {"READY", "BUSY"}
```

An **assertion** checks a condition and fails a test when it is false. `pytest.approx(expected)` compares numbers while allowing small rounding differences. An **exception** is Python's way of reporting an error; `with pytest.raises(ValueError):` passes only if the indented operation raises that exception.

A **marker** is a label attached to a test, such as `@pytest.mark.slow`. **Registering** a marker means listing its name in `pytest.ini`, pytest's settings file; `slow` is already registered here. **Deselection** means leaving a test out of a run; `-m "not slow"` selects tests without the `slow` label. A marker does not add a delay.

An **id** is a readable label for one parametrized row, visible in pytest's output. **Data wrangling** means turning raw text into useful information. On a Linux station, `grep` selects matching log lines, `sed` transforms text, and `awk` extracts fields or computes values. Descriptive case ids make those log searches easier. No shell commands are required in this set.

A **mutant** is a deliberately faulty driver copy. Our outer checks start a **subprocess**, a separate Python process, to run your tests with the supplied driver and these copies. Good tests pass on the supplied driver and fail on the relevant mutants. Write assertions against the imported driver functions; do not inspect files or detect which driver is loaded. The supplied `conftest.py` keeps your tests out of the outer collection so the score still has four exercises.

## Supplied driver: `scpi.py`

An import makes another module's functions available in your file. The imports are already in your starter. You do not implement this driver.

| Function | Contract |
| --- | --- |
| `parse_number(reply: str) -> float` | Convert a decimal or scientific-notation string to a number. Ignore spaces and line endings at its edges. Nonnumeric text raises `ValueError`. Scientific notation uses `E` for a power of ten: `6.02E+2` means `6.02 × 100`. |
| `parse_error(reply: str) -> tuple[int, str]` | Split a reply at its first comma into a signed integer code and a quoted message. Ignore outer whitespace and spaces before the opening quote; remove the message's surrounding quotes. Preserve its capitalization, internal spaces, and internal commas. A tuple is a fixed sequence, here `(code, message)`. Invalid integer codes, missing commas, and missing surrounding message quotes raise `ValueError`. Embedded quote escapes are outside this exercise. |
| `build_query(channel: int) -> str` | For a positive integer channel, return exactly `MEAS:VOLT? (@<channel>)\n`. A channel is a numbered instrument input; a query is a command asking for a reading. Zero or negative channels raise `ValueError`. |
| `read_voltage(reply: str) -> float` | Normally call `parse_number`. The special reply `"OVLD"` means overload: the input exceeds the instrument's measurement range. Known firmware defect **FW-17** incorrectly returns `0.0` for `"OVLD"`. The desired behavior is to raise `ValueError("overload")`. Firmware is the software running inside an instrument. |

In Python string literals, `\r` means carriage return and `\n` means newline; together they are a common instrument line ending. Type these escapes inside strings rather than entering a physical line break.

## Exercises

### E1 — Voltage formats (easy, ~11 min)

**Goal:** Parametrize one station voltage test over at least these six cases.

**Signature:** `def test_e1_number_reply(reply: str, expected: float) -> None`

Add `@pytest.mark.parametrize` with the parameter names `"reply, expected"` and the following rows. Extra valid rows are welcome.

| `reply` as a Python string literal | `expected` |
| --- | --- |
| `"0"` | `0.0` |
| `"-12"` | `-12.0` |
| `"+3.5"` | `3.5` |
| `"6.02E+2"` | `602.0` |
| `" 7.25 "` | `7.25` |
| `"8.5\r\n"` | `8.5` |

The body must call `parse_number(reply)` and assert that it equals `expected`; direct equality or `pytest.approx` is fine.

**Example:** `parse_number("6.02E+2")` → `602.0`.

**Watch out:** A loop inside an undecorated test does not create six pytest cases. Check the returned value, not just whether a call completes. Your test must catch lost minus signs, ignored exponents, and rejection of surrounding whitespace.

**Reread:** pytest How to parametrize, section “@pytest.mark.parametrize: parametrizing test functions.”

### E2 — Searchable instrument errors (easy, ~12 min)

**Goal:** Parametrize one error-queue test so an operator can find the failing reply format by its id. An error queue is the instrument's stored list of problems; code zero means it has no error to report.

**Signature:** `def test_e2_error_reply(reply: str, expected: tuple[int, str]) -> None`

Use `@pytest.mark.parametrize` with `"reply, expected"` and these four rows. Each `expected` value is one tuple.

| `reply` as a Python string literal | `expected` |
| --- | --- |
| `'0,"No error"'` | `(0, "No error")` |
| `'-100,"Command error"'` | `(-100, "Command error")` |
| `' -222, "Data out of range"\r\n'` | `(-222, "Data out of range")` |
| `'-300,"Relay, stuck"'` | `(-300, "Relay, stuck")` |

Assign each row a distinct explicit id, either through `ids=[...]` on the decorator or `pytest.param(..., id="...")`. Use nonempty ASCII letters, digits, and hyphens only, with at least one letter; for example, `queue-clear`. ASCII here means ordinary English letters and digits. You choose the names. Extra valid rows need ids too.

The body must call `parse_error(reply)` and assert equality with the entire `expected` tuple.

**Example:** `parse_error('-300,"Relay, stuck"')` → `(-300, "Relay, stuck")`.

**Watch out:** A message can contain a comma. Check signed codes and the exact full message, including capitalization. Generated default ids are not a substitute for the explicit readable ids requested here.

**Reread:** pytest How to parametrize, examples using `ids` and `pytest.param`; Missing Semester Data Wrangling, the `grep`, `sed`, and `awk` examples for finding and extracting useful log text.

### E3 — Select the quick station run (medium, ~10 min)

**Goal:** Label the station sweep so an operator can omit it during a quick run. A sweep checks several instrument channels in sequence.

**Signature:** `def test_e3_station_sweep() -> None`

Add `@pytest.mark.slow`. Inside this single test, call `build_query` for channels `1`, `2`, and `3` and assert each complete command equals its expected string. A loop is appropriate here. Include the space before `(@...)` and the final newline.

**Example:** `build_query(2)` → `"MEAS:VOLT? (@2)\n"`.

The set's `pytest.ini` already registers `slow`. Our checks run pytest with `-m "not slow"` and verify that only your sweep is deselected, while other tests remain selected. You do not need to launch subprocesses yourself.

**Watch out:** Put the marker only on this function, not on the whole module. Do not sleep or connect to hardware: this model stands in for a slow physical sweep and finishes immediately. The assertions must catch a driver that always queries channel 1.

**Reread:** pytest How to mark test functions, “Registering marks” and “Marking test functions and selecting them for a run.”

### E4 — Keep the firmware defect visible (medium, ~12 min)

**Goal:** Record the desired overload behavior while acknowledging the known FW-17 defect.

**Signature:** `def test_e4_overload_quirk() -> None`

Use `@pytest.mark.xfail(reason=..., strict=True)`. An **xfail** marks a test whose failure is expected because of a known defect. Supply a nonempty reason that names `FW-17` and explains the overload problem.

Inside the test, use `with pytest.raises(ValueError, match="overload"):` around `read_voltage("OVLD")`. The `match` argument checks the exception's message. Test the desired exception, even though the supplied driver currently returns zero.

**Example:** Current firmware returns `0.0`, so the desired-behavior test is reported as **XFAIL**, an expected failure. Our repaired driver raises `ValueError("overload")`, so that same test becomes **XPASS**, an unexpected pass.

**Watch out:** `strict=True` makes XPASS fail the run, reminding the team to remove the obsolete xfail once firmware is repaired. Do not assert the buggy zero result, skip the test, call `pytest.xfail()` yourself, or set `run=False`; the test body must execute. An ordinary **skip** omits a test without checking the known defect.

**Reread:** pytest How to mark test functions, the built-in `xfail` marker and linked “How to use skip and xfail”; pytest How to parametrize, the `pytest.param` example with an xfail mark.
