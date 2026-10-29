# d02 — Pass or fail? Decisions, loops and functions

**Time:** about 45 minutes · **Read first:** [Python Tutorial §4.1–4.8: if, for, range, functions](https://docs.python.org/3/tutorial/controlflow.html), [Automate the Boring Stuff ch. 3: functions, scope, return values, None](https://automatetheboringstuff.com/2e/chapter3/), and [The Linux Command Line ch. 2–4: navigation, exploring, manipulating files](https://linuxcommand.org/tlcl.php) · **You edit:** `starter/decide.py`

## What you're building

A test station is a computer connected to equipment that measures or controls hardware. Its power supply provides a chosen voltage, and each reading is one measured voltage value. You'll turn readings into pass/fail decisions and find when the output settles: stays close enough to the requested voltage for several readings in a row.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/decide.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d02** (or run `bash tools/run.sh d02` / `tools\run.ps1 d02` from the repository root). At first you'll see `Exercises: 0 / 4 passed`. Save and rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **function** is a named block of code; its **parameters** are the named inputs in its definition.
A **return value** is the result sent back by `return`; printing a result does not return it.
**Scope** is where a name can be used; a variable assigned inside a function is normally local to that call.
A **condition** is an expression that is true or false; `if` chooses which code runs.
A **loop** repeats code; `for` visits items in order, and `range(n)` supplies integers from 0 through `n - 1`.
A **list** is an ordered collection; an **index** is an item's position, starting at 0.
`None` means no value; check it with `is None`, since the number 0 is a valid value.
A **type hint** describes an expected type: `float` is a number, `int` an integer, `str` text, and `float | None` allows a number or `None`.

A **channel** is one separately identified input or output connection on station equipment. For example, this function returns how many channels have even-numbered positions:

```python
def count_even_channels(channel_count: int) -> int:
    count = 0
    for index in range(channel_count):
        if index % 2 == 0:  # % gives the remainder after division
            count += 1
    return count
```

All inputs in this set are ordinary finite numbers (no infinity or special not-a-number values). Where both limits exist, `low <= high`. For E4, `tolerance >= 0` and `hold >= 1`; you do not need to validate inputs outside these rules. Return results without printing and leave input lists unchanged. You may call your earlier functions from later ones, but it is optional.

## Exercises

### E1 — Classify a reading (easy, ~8 min)

**Goal:** A **limit** is an allowed boundary for a measurement. Return exactly `"LOW"` if the reading is below the lower limit, `"HIGH"` if it is above the upper limit, and `"PASS"` otherwise.

**Signature:** `def classify(value: float, low: float | None, high: float | None) -> str`

**Example:** `classify(4.5, 4.5, 5.5)` → `"PASS"`; `classify(0.0, None, 5.5)` → `"PASS"`.

**Watch out:** Limits are **inclusive**, meaning equality passes. `None` means **unbounded**: there is no limit on that side. Both limits may be `None`, so any supplied reading passes. A limit of `0.0` is still a real limit.

**Reread:** Python Tutorial §4.1 (if statements), §4.7 (defining functions), §4.8.1 (default argument values, including the `is None` example); Automate the Boring Stuff ch. 3, “Return Values and return Statements.”

### E2 — Count failing readings (easy, ~8 min)

**Goal:** A **failure** is a reading strictly below `low` or strictly above `high`. Return the number of failures in a batch, which is a list of readings collected by the station.

**Signature:** `def count_failures(values: list[float], low: float, high: float) -> int`

**Example:** `count_failures([4.0, 4.5, 5.0, 5.5, 6.0], 4.5, 5.5)` → `2`.

**Watch out:** Both limits are numbers in E2 and E3. Equality passes. Count each failing reading, including repeated values. An empty list returns `0`.

**Reread:** Python Tutorial §4.1–4.2 (if statements and for statements), §4.7 (defining functions); Automate the Boring Stuff ch. 3, “Local and Global Scope.”

### E3 — Find the first failure (easy–medium, ~10 min)

**Goal:** Help the operator locate the first failing reading in collection order. Return its index, or `None` if all readings pass.

**Signature:** `def first_out_of_limits(values: list[float], low: float, high: float) -> int | None`

**Example:** `first_out_of_limits([5.0, 5.5, 6.0, 4.0], 4.5, 5.5)` → `2`.

**Watch out:** The first item's index is `0`, which is different from `None`. Both boundaries pass. Return `None` for an empty list. Return the index, not the reading or the number of failures.

**Reread:** Python Tutorial §4.3 (range), §4.7 (return); Automate the Boring Stuff ch. 3, “The None Value” and “Return Values and return Statements.”

### E4 — Wait for the supply to settle (medium, ~19 min)

**Goal:** The **target** is the requested voltage. The **tolerance** is the allowed distance above or below it. A reading is within tolerance when `target - tolerance <= reading <= target + tolerance`. The **hold** is the number of consecutive readings (adjacent items, with no gaps) required before the station accepts the supply as settled. Return the starting index of the earliest complete run of `hold` readings within tolerance.

**Signature:** `def settle_index(values: list[float], target: float, tolerance: float, hold: int) -> int | None`

**Example:** `settle_index([0.0, 4.75, 5.25, 5.0, 6.0], 5.0, 0.25, 3)` → `1`. The readings at indices 1, 2, and 3 form the first complete run.

**Watch out:** Return the run's start, not the index where the run finishes. Any reading outside tolerance breaks a run; earlier good readings do not count toward the next one. Return `None` if no complete run exists, including for an empty list or `hold > len(values)`. For `hold == 1`, return the first within-tolerance index. Zero tolerance requires equality with the target. Boundaries pass; compare values as supplied without rounding. A later bad reading does not cancel a run that was already complete.

**Reread:** Python Tutorial §4.1–4.3 (conditions, loops, range), §4.7 (functions); Automate the Boring Stuff ch. 3, “Local Variables Cannot Be Used in the Global Scope” and “Return Values and return Statements.”
