# r2 — Block 2 station review

**Time:** about 60 minutes · **Read first:** review day, no new reading. Revisit the earlier readings listed below as needed. · **You edit:** `starter/review2.py` and `starter/test_review2_learner.py`.

## What you're building

A chassis test station measures current, summarizes step results, and shows an operator recent problems. This set mixes this week with earlier weeks: implement this week's three helpers and two test exercises, then revisit week 1 CSV files and exceptions with two new problems. Everything uses simulated results; no instruments are connected.

Readings to revisit from d08-d15, plus d04-d05 for the final two exercises:

- Python Tutorial section 6, "Modules"; `typing` documentation introduction; mypy "Getting started".
- pytest "Get started", "How to write and report assertions", "How to use fixtures" (including `tmp_path`), and "How to parametrize".
- Python Logging HOWTO; `collections` documentation for `Counter`, `defaultdict`, and `deque`.
- *A Common-Sense Guide to Data Structures and Algorithms*, chapters introducing Big O and stacks and queues.

## How this works

1. Replace the `raise NotImplementedError(...)` lines for E1-E3 and E6-E7 in `starter/review2.py` and E4-E5 in `starter/test_review2_learner.py`. Leave the supplied `current_status` and `log_status` helpers alone. Don't edit `tests/` or `conftest.py`.
2. Press Ctrl+Shift+B → **Test: r2** (or run `bash tools/run.sh r2` / `tools\run.ps1 r2`). At first you'll see `Exercises: 0 / 7 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **module** is a Python file you can import. A **type hint**, such as `-> float`, states what kind of value code expects; **mypy** checks those hints without running the functions. E1 includes a `mypy --strict` check of the entire `review2.py` module: keep its supplied annotations and annotate any helpers you add. A mypy message gives a file, a line, and a type mismatch to fix.

A **status** is a step's outcome: `PASS` means its requirement was met, `FAIL` means a measurement failed its requirement, and `ERROR` means the station could not complete the step. A **deque** (pronounced "deck") is a queue with efficient insertion and removal at either end. A **window** is a fixed number of consecutive results. A **running count** changes only for the entering and departing result; it avoids counting a whole window again.

An **iterable** supplies values in a loop; an **iterator** supplies them once, so it cannot be restarted or indexed. **O(n)** means work grows roughly in proportion to the number of input results. **O(window)** working storage means retaining only about one window, apart from the output list.

A pytest **fixture** supplies a test resource through a function argument. An **assertion** checks a condition; `pytest.raises` checks that a call raises an expected exception. **Parametrization** runs a test with several sets of arguments. A **mutant** is an intentionally broken helper: your tests must pass with the correct helper and fail with every mutant. An import error does not count as finding a defect.

For example, this independent test checks an operator's millisecond interval:

```python
import pytest

@pytest.mark.parametrize("milliseconds,seconds", [(500, 0.5), (2000, 2.0)])
def test_interval(milliseconds: int, seconds: float) -> None:
    assert milliseconds / 1000 == pytest.approx(seconds)
```

## Exercises

### E1 — Typed current conversion (easy, ~4 min)

**Goal:** Normalize an instrument's current into amperes, abbreviated `A`. A milliampere (`mA`) is 0.001 A; a microampere (`uA`) is 0.000001 A.

**Signature:** `def current_in_amps(value: float, unit: str) -> float`

Accept exactly `A`, `mA`, or `uA`, with case and whitespace unchanged. Return the converted number. Unknown units raise `ValueError`; do not strip whitespace or change case. Inputs are finite numbers (neither infinity nor NaN, the floating-point "not a number" value); negative and zero values are valid.

**Example:** `current_in_amps(250.0, "mA")` → `0.25`.

**Watch out:** `MA`, `ma`, and `" mA"` are unknown units. Your completed module must also pass mypy in strict mode. You can use the imports already supplied.

**Reread:** d08: Python Tutorial section 6, "Modules"; `typing` introduction; mypy "Getting started", especially function annotations and error messages.

### E2 — Summarize the station run (easy, ~7 min)

**Goal:** Count outcomes and choose the worst status for the operator.

**Signature:** `def summarize(statuses: list[str]) -> tuple[dict[str, int], str]`

Accept only the exact strings `PASS`, `FAIL`, and `ERROR`. Return `(counts, overall)`, where `counts` always contains these three keys, including zero counts. `ERROR` takes priority over `FAIL`, which takes priority over `PASS`. Empty input returns all zero counts and overall `NOT_RUN`. Any other string raises `ValueError`. Do not change the input; return a new counts dictionary for each call.

**Example:** `summarize(["PASS", "FAIL", "PASS"])` → `({"PASS": 2, "FAIL": 1, "ERROR": 0}, "FAIL")`.

**Watch out:** `"pass"` and `"ERROR "` are invalid. A `Counter` is a dictionary-like counter from `collections`; it can help, but is optional.

**Reread:** d13: `collections` documentation, `Counter` and counting examples.

### E3 — Recent problems in a bounded window (medium, ~10 min)

**Goal:** Count bad steps in each full window so the operator can see recent station health. A bad step is either `FAIL` or `ERROR`.

**Signature:** `def rolling_bad_counts(statuses: Iterable[str], window: int) -> list[int]`

`window` is an integer. If it is less than 1, raise `ValueError` before consuming any input. Otherwise consume the iterable once. Each string must be exactly `PASS`, `FAIL`, or `ERROR`; any other string raises `ValueError`, even when there are too few results to fill a window. Return one bad count for every full window, in arrival order. Empty input or fewer than `window` valid results returns `[]`.

Use a deque and a running count: add the incoming status, remove the oldest when necessary, adjust the count for each, and emit only when the window is full. Aim for O(n) work and O(window) working storage, excluding the output. Do not turn the entire iterable into a list. The check streams 200,000 results with a window of 5,000 and allows 2 seconds.

**Example:** `rolling_bad_counts(iter(["PASS", "FAIL", "ERROR", "PASS", "PASS"]), 3)` → `[2, 2, 1]`.

**Watch out:** A window of 1 produces one count per result. Do not emit a partial window at the start or end. Treat both failure statuses as bad.

**Reread:** d15: `collections.deque`, especially `append` and `popleft`; *A Common-Sense Guide to Data Structures and Algorithms*, Big O and queues.

### E4 — Write tests for inclusive current limits (medium, ~9 min)

**Goal:** In `starter/test_review2_learner.py`, write pytest tests of the supplied `current_status(value: float, low: float, high: float) -> str` helper. All three numbers are in amperes. The **limits** are the acceptable lower and upper current values; **inclusive** means equality passes.

The helper's complete contract:

- Return `LOW` below `low`, `HIGH` above `high`, and `PASS` between them, including both endpoints.
- Equal limits are valid: equality passes, anything smaller is `LOW`, and anything larger is `HIGH`. Negative limits are allowed.
- Raise `ValueError` if `low > high` or if **any** argument is NaN or positive/negative infinity. This validation takes priority over classification. Exception messages are not part of the contract.

**Example:** `current_status(0.2, 0.2, 0.8)` → `"PASS"`.

Replace the three E4 stubs. The supplied parameter rows already cover below/inside/above the range, both endpoints, and equal limits; compare the helper's result to `expected`. The other two stubs check reversed limits and non-finite numbers, so you can focus on assertions rather than choosing test inputs. For the non-finite test, start with `[1.5, 1.0, 2.0]`, replace item `position` with `number`, and call the helper with those three arguments (or unpack the list with `*arguments`). You may add more `test_e4_*` functions, but none are required. Use `float("nan")`, `float("inf")`, and `-float("inf")` to construct the latter. Use `with pytest.raises(ValueError):` around a call that must be rejected.

The checks run only your `test_e4_*` tests against the correct helper and four separate defects: rejecting the lower endpoint, rejecting the upper endpoint, accepting reversed limits, and accepting non-finite values. All tests must pass against the correct helper; at least one assertion or `pytest.raises` check must fail for each defect. Do not skip tests, use `xfail`, or inspect the helper's implementation.

**Watch out:** Don't implement a replacement checker inside the tests. Import the supplied helper and assert its observable result. E4 is independent of whether you finished E1-E3.

**Reread:** d09: pytest "Get started" and "How to write and report assertions", expected exceptions; d12: "How to parametrize", parameter sets.

### E5 — Write tests for operator logs (medium, ~9 min)

**Goal:** Test the supplied `log_status(logger: logging.Logger, channel: str, status: str) -> None` helper in the same learner test file.

A **logger** sends diagnostic messages. Each message creates a **log record** with a level and text. `INFO` is routine information; `WARNING` flags an issue. A **channel** is a named measurement connection, such as `I7`. Here `status` is guaranteed to be `PASS` or `FAIL`, and `channel` is a string used exactly as given; other inputs need no validation.

Each call must emit exactly one record through the given logger. A `PASS` record has level `logging.INFO`; a `FAIL` record has level `logging.WARNING`. The formatted text is exactly `"{channel}: {status}"`, with a colon and one space. The function returns `None`; timestamps and handler configuration are outside this exercise.

**Example:** logging channel `I7` with `FAIL` emits one WARNING record whose message is `"I7: FAIL"`.

Replace the E5 stub and keep its supplied arguments. The decorator already runs it for both statuses and supplies `expected_level`; you only write the capture and assertions. No additional test functions or parameter rows are required. **caplog** is pytest's fixture for capturing log records; enable INFO capture before calling the helper. Use a named logger from `logging.getLogger(...)`. Check the count, numeric level (`record.levelno`), and formatted text (`record.getMessage()`) for both statuses. You can select records by `record.name == logger.name`. If you make several calls in one test, use `caplog.clear()` between them or account for earlier records.

This independent example shows how to enable capture:

```python
logger = logging.getLogger("station.connection")
with caplog.at_level(logging.INFO, logger=logger.name):
    logger.info("connection ready")
assert caplog.records[-1].getMessage() == "connection ready"
```

Your E5 tests must accept the correct helper and catch three defects separately: FAIL logged at INFO, missing channel in the message, and duplicate records. Do not skip tests or use `xfail`. The supplied checks run E5 separately from E4, so unfinished E4 tests do not block E5.

**Watch out:** Checking only `caplog.text` can miss a wrong level or duplicate record. INFO is normally filtered out unless capture is enabled.

**Reread:** d11: pytest "How to use fixtures", fixture arguments and per-test isolation; d13: Logging HOWTO, logging levels and named loggers; d09: assertion reporting.


### E6 — Load a station's limit bands (easy–medium, ~12 min)

**Goal:** Read the allowed range for each measurement channel from a CSV file. A **limit band** is the pair `(low, high)` of acceptable boundaries, including equality at either boundary. Each boundary is called a **bound**.

**Signature:** `def load_limit_bands(path: str | Path) -> dict[str, tuple[float, float]]`

CSV means comma-separated values: a text table with a header naming its columns. The header is exactly `channel,low,high`; each record has those three fields. Use `csv.DictReader` and open the file with `encoding="utf-8", newline=""`. A `Path` represents a file location; `Path(path)` accepts either allowed input type. A `with` block closes the file even if a row fails.

Return a dictionary mapping each channel to its limits as a tuple of floats. Preserve channel text exactly, including spaces, capitalization, non-English characters, and quoted commas. Skip completely empty lines. A header-only file returns `{}`. Dictionary order does not matter. A duplicate is a channel whose exact text has already appeared. Reject duplicates with `ValueError`, even when both bands are identical. Include `line N` in the error message, where `N` is the repeated record's source line number. Use the reader's `line_num`: the header is line 1, empty lines count, and a quoted record spanning several lines uses its final line.

**Example:** A file containing `channel,low,high`, then `BUS_V,27,29` and `I7,0,0` on separate lines returns `{"BUS_V": (27.0, 29.0), "I7": (0.0, 0.0)}`.

**Watch out:** Negative and equal limits are valid. Reject a row with `ValueError` if either bound cannot be converted with `float()`, is non-finite (NaN or positive/negative infinity), or if `low > high`. `math.isfinite(number)` returns `True` only for a finite number; converting text with `float()` alone does not reject NaN or infinity. Reject any bad row immediately, even if the channel appears again later. A missing file raises `FileNotFoundError`. Do not change the file, print results, or return partial data after an error. Header and field-count validation are outside this exercise.

Reread: d04

### E7 — Translate a station readiness reply (easy–medium, ~9 min)

**Goal:** Ask an instrument whether it is ready, while distinguishing a timeout from a bad reply. A **query** is a callable that accepts a command string and returns the instrument's text reply; the tests supply it, so no hardware is needed. A **timeout** means the instrument did not answer in time.

**Signature:** `def station_readiness(query: Callable[[str], str]) -> str`

Call `query("STAT:READY?")` exactly once. Remove surrounding whitespace from its reply. Reply `"1"` returns `"READY"`; reply `"0"` returns `"BUSY"`. Any other reply raises `ValueError`; exception messages are not checked. In this simulated station, `STAT:READY?` is the command for reading the readiness flag.

If the query raises Python's built-in `TimeoutError` (including a subclass), return `"OFFLINE"`. Propagate every other exception unchanged: let the caller receive the same exception object. Do not retry, sleep, print, or convert other failures into `OFFLINE`. The input callable and its returned value match the supplied type hints.

**Example:** If the supplied query returns `" 1\r\n"`, return `"READY"`; if it raises `TimeoutError("link silent")`, return `"OFFLINE"`.

**Watch out:** Use `try`/`except TimeoutError` around the query. A broad `except Exception` would hide failures such as a rejected command. `"01"` and `"ready"` are invalid replies, even though they might look meaningful to an operator.

Reread: d05
