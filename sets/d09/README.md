# d09 — Your first pytest tests

**Time:** about 45 minutes (5 minutes to read and run, then 40 minutes of exercises) · **Read first:** [pytest: Get started](https://docs.pytest.org/en/stable/getting-started.html), [pytest: How to write and report assertions](https://docs.pytest.org/en/stable/how-to/assert.html), and [Missing Semester: Shell Tools and Scripting (first half, Shell Scripting)](https://missing.csail.mit.edu/2020/shell-tools/) · **You edit:** `starter/test_limits_learner.py`

## What you're building

A chassis test station checks instrument readings against allowed limits before showing an operator a result. Here the checker is supplied and correct: your job is to write tests that protect it from future mistakes. A **mutant** is a deliberately broken copy of that checker; a useful test passes on the correct copy and fails on a mutant.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/test_limits_learner.py` with test code. Keep the four function names, their empty argument lists, and the supplied imports. Do not edit `starter/limits_lib.py`, `conftest.py`, or `tests/`.
2. Press **Ctrl+Shift+B → Test: d09** (or run `bash tools/run.sh d09` / `tools\run.ps1 d09` from the repository root). At first you'll see `Exercises: 0 / 4 passed`. Save and rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

The grader runs each exercise's test on the correct checker, then uses a fresh Python process (a separate running copy of Python) to run it on each matching mutant in `tests/mutants/`. Each mutant breaks one required scenario, so your test must catch them all to pass the exercise. A failure naming a mutant means your test allowed its faulty behavior. An unfinished test cannot earn credit by failing on every checker. The learner test file is excluded from ordinary collection because these grading checks run it themselves.

A **test** is a function that checks expected behavior; pytest finds names starting with `test_`. An **assertion**, written `assert condition`, fails if its condition is false. pytest shows the values involved, so assert the actual returned value against the expected value. Calling a function without checking its result does not test its result.

**Floating-point numbers** represent decimals approximately in memory. `pytest.approx(expected)` checks numeric equality with a small tolerance (an allowed numerical difference). A **context manager** is a `with` block; `pytest.raises(ErrorType)` passes only if that block raises the named exception (an error Python signals while running). This unrelated station example shows all three tools:

```python
assert "station ready".startswith("station")
measured_volts = 0.1 + 0.2
assert measured_volts == pytest.approx(0.3)
with pytest.raises(ValueError):
    float("instrument offline")
```

`classify` returns text, so use exact `==` comparisons here; `approx` is for numeric results. Keep each `raises` block around just the call expected to raise. A runner's **exit code** is its numeric success/failure result, as in the shell reading: zero means success. The grader checks pytest's result for you; you do not need to write shell scripts or process code.

## Supplied checker contract

**Signature:** `def classify(value: float | None, low: float, high: float) -> str`

Import it with the supplied `from starter.limits_lib import classify`. A **limit window** is the allowed interval from `low` to `high`. Bounds are **inclusive**: a reading equal to either endpoint is allowed. A **NaN** ("not a number") is an invalid numeric reading, made with `float("nan")`. Use **finite** numbers (ordinary numbers, excluding infinity and NaN) for both limits. The reading may be a finite number, `None`, or NaN. Other inputs are outside this set's contract.

The checker applies these rules in this exact order:

| Condition | Result |
| --- | --- |
| `low > high`, for any permitted reading | Raise `ValueError`; do not silently exchange the limits |
| Reading is `None` (Python's marker for an absent value) | `"MISSING"` |
| Reading is NaN | `"INVALID"` |
| Finite reading below `low` | `"LOW"` |
| Finite reading above `high` | `"HIGH"` |
| Finite reading inside the window or on either bound | `"PASS"` |

When `low == high`, that one exact finite reading passes. Exception message text is not part of the contract. Tests must call the supplied checker and assert its behavior; don't replace it or deliberately fail. No fixtures (pytest-supplied test inputs) or parametrization (running a test with multiple input cases) are needed yet: several assert lines in one function are enough.

## Exercises

### E1 — Protect voltage boundaries (easy, ~12 min)

**Goal:** Check a power-supply voltage window. Write assertions for a reading below the window, at the lower bound, inside it, at the upper bound, and above it. Also check a window whose two limits are equal. The mutants break the six required cases separately, including each endpoint and the equal-limit window.

**Signature:** `def test_e1_inclusive_bounds() -> None:`

**Example:** `classify(12.0, 10.0, 14.0)` → `"PASS"`; `classify(9.0, 10.0, 14.0)` → `"LOW"`.

**Watch out:** A test using only a middle reading will miss the boundary fault. Choose simple exact numbers for endpoint comparisons; there is no numeric tolerance in the checker's inclusive rule.

**Reread:** pytest Get started, "Create your first test"; How to write and report assertions, "Asserting with the assert statement".

### E2 — Protect missing instrument readings (easy, ~8 min)

**Goal:** Verify that an absent instrument reading returns `"MISSING"`. Call the checker with `None` using two different valid limit windows, one positive and one negative. Separate mutants report an absent reading as `"PASS"` in positive and negative windows.

**Signature:** `def test_e2_missing_reading() -> None:`

**Example:** `classify(None, 10.0, 14.0)` → `"MISSING"`.

**Watch out:** Use `None`, not the string `"None"` or a zero reading. Missing data must never look like a successful measurement.

**Reread:** pytest How to write and report assertions, "Asserting with the assert statement".

### E3 — Protect invalid numeric readings (easy, ~8 min)

**Goal:** Verify that an invalid numeric instrument reading returns `"INVALID"`. Make a NaN with `float("nan")` and check it using two different valid windows, one positive and one negative. Separate mutants let NaN return `"PASS"` in positive and negative windows.

**Signature:** `def test_e3_nan_reading() -> None:`

**Example:** `classify(float("nan"), 10.0, 14.0)` → `"INVALID"`.

**Watch out:** NaN compares unequal even to itself, so don't assert that the input equals NaN. Assert the returned status string. NaN and `None` represent different station problems.

**Reread:** pytest How to write and report assertions, "Asserting with the assert statement" and its failure-output examples.

### E4 — Reject reversed station limits (medium, ~12 min)

**Goal:** Use `pytest.raises(ValueError)` to check reversed limits with three readings: a finite number between the two endpoints, `None`, and NaN. Separate mutants skip limit validation for each of these three kinds of reading.

**Signature:** `def test_e4_reversed_limits() -> None:`

**Example:** `classify(12.0, 14.0, 10.0)` → raises `ValueError`.

**Watch out:** Use a separate `with pytest.raises(ValueError):` block for each call. Python stops that block at the first exception, so three calls inside one block would check only the first. Limit validation happens before missing/invalid reading handling. Equal limits are valid, as E1 checks.

**Reread:** pytest Get started, "Assert that a certain exception is raised"; How to write and report assertions, "Assertions about expected exceptions".
