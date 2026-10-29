# d13 — Practical speed: big-O on sensor data

**Time:** about 45 minutes · **Read first:** *A Common-Sense Guide to DSA*, the first chapters on Big O and the chapters on stacks and queues (your book; skip the end-of-chapter exercises because this set is today's practice); [Python `collections.deque` documentation](https://docs.python.org/3/library/collections.html#collections.deque); [Missing Semester: Version Control (git's data model)](https://missing.csail.mit.edu/2020/version-control/) · **You edit:** `starter/windows.py`

## What you're building

A chassis test station records thousands of sensor readings each second. Build helpers that smooth those readings, show the largest recent reading, flag sudden increases, and remove repeated instrument serial numbers before an operator sees the report.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/windows.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d13** (or run `bash tools/run.sh d13` / `tools\run.ps1 d13`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

Allow about 2 minutes to read these shared rules, then use the exercise times below.

- An **index** is a position in a list, starting at zero. Readings arrive in list order.
- A **window** is a consecutive group of `window` readings. A **full window** has exactly that many readings; partial groups produce no output.
- A **mean** is the sum divided by the number of readings. A **running sum** keeps a total and updates it when one reading leaves and another enters.
- **Big O** describes how work grows as input grows. Here `n` is the number of input items: **O(n)** means linear work (roughly twice the work for twice the data); **O(n × window)** means rescanning every window. **O(1)** means constant work per operation, independent of input length.
- A **stack** removes the newest item first; a **queue** removes the oldest item first. A **deque** (double-ended queue, pronounced "deck") supports adding/removing at either end in O(1): `append` adds right, `pop` removes right, and `popleft` removes left. Accessing either end with `[0]` or `[-1]` is also O(1). Avoid `list.pop(0)`, which shifts the remaining items.
- A **set** stores distinct items and supports membership (`item in seen`) in average O(1). Keep a separate list when output order matters.

This short deque example holds pending station messages; it is not a sliding-window calculation:

```python
from collections import deque
pending = deque(["read CH1", "read CH2"])
pending.append("read CH3")
next_step = pending.popleft()  # "read CH1"
```

Shared contracts: return a new list where a list is requested; never change an input list. For E1–E3, `window` is an integer: raise `ValueError` when it is zero or negative, even for empty input. Otherwise a window longer than the input is valid. Inputs have the annotated types; readings and factors are finite numbers (no infinity or NaN, meaning "not a number"), with ordinary sensor magnitudes. You need not validate those preconditions. Small floating-point rounding differences in means are accepted.

E1, E2 and E4 have timed checks allowing **2 seconds per function call**, excluding input construction. E1 and E2 use 200,000 readings with a window of 1,000. Additional small checks count how many readings your code accesses and, for E1, additions on the readings (even after copying the list), so repeated window slicing/scanning fails even on fast machines. Use linear algorithms; avoid recalculating every sum or maximum and checking membership in a growing output list.

The git reading supports today's workflow: a **commit** records a snapshot of tracked files and its parent history; a **branch** is a name pointing to a commit. Spend a moment relating this to saving a working exercise version in your own clone. No git commands are graded today.

## Exercises

### E1 — Smooth a sensor trace (easy, ~10 min)

**Goal:** Return the mean of each full window, moving one reading right each time. Output element `j` summarizes `values[j:j + window]`. There are `max(0, len(values) - window + 1)` outputs. Use O(n) total work.

**Signature:** `def rolling_mean(values: list[float], window: int) -> list[float]`

**Example:** `rolling_mean([2.0, 4.0, 8.0, 10.0], 2)` → `[3.0, 6.0, 9.0]`

**Watch out:** Empty input or a window longer than the list returns `[]`. A window of one returns the readings; a window equal to the list length returns one mean. Compute the first total once, then remove the outgoing reading and add the incoming one. Negative readings are allowed.

**Reread:** *A Common-Sense Guide to DSA*, Big O chapters: counting operations inside loops and nested loops.

### E2 — Largest recent load (medium, ~17 min)

**Goal:** Return the largest value in each full window, in the same output order and count as E1. Use a monotonic deque of candidate indices for O(n) total work. **Monotonic** here means their values never increase from the front to the back.

**Signature:** `def max_in_windows(values: list[float], window: int) -> list[float]`

**Example:** `max_in_windows([4.0, 2.0, 3.0, 1.0, 5.0], 3)` → `[4.0, 3.0, 5.0]`

Build the idea one step at a time:

1. Store indices in the deque, oldest at the left. Indices let you tell when a reading has left the current window.
2. At incoming index `i`, the window starts at `i - window + 1`. Remove indices smaller than that start from the left.
3. Remove indices from the right while their readings are less than or equal to the incoming reading. The incoming reading is at least as large and will remain in the window longer, so those older candidates cannot be needed again.
4. Append `i` to the right. The front now points to the largest reading still in the window.
5. Only append a maximum to the result once `i >= window - 1`, when the first full window exists.

For the example, at index 2 the candidates are `[0, 2]`, holding values `[4.0, 3.0]`, so emit `4.0`. At index 3, index 0 expires; the candidates become `[2, 3]` and emit `3.0`. At index 4, the new `5.0` removes both smaller candidates and emits `5.0`.

**Watch out:** Empty or too-short input returns `[]`. Negative values and repeated maxima work normally. Each index enters once and leaves at most once, so the loops together do O(n) work even though one loop is inside another. The deque needs at most O(window) storage, plus the output list.

**Reread:** *A Common-Sense Guide to DSA*, stacks and queues chapters; `collections.deque` docs: `append`, `pop`, `popleft`, and the performance discussion.

### E3 — First sudden increase (medium, ~10 min)

**Goal:** A **spike** is a reading strictly greater than `factor` times the mean of the immediately preceding `window` readings. Return the first spike's original index, or `None` if none exists. Begin checking at index `window`; exclude the current reading from its baseline (the preceding mean). Use a running sum for O(n) total work.

Floating-point arithmetic can slightly shift an equal threshold. Treat a reading and its threshold as equal when `math.isclose(reading, threshold, rel_tol=1e-9, abs_tol=1e-12)` is true; equal readings are not spikes. Here `rel_tol` allows a difference up to one billionth of the larger absolute value, and `abs_tol` allows a difference up to `1e-12` near zero. Exceeding either allowance alone is not enough: a spike must be above the threshold and outside both allowances. You can import `math` or use an equivalent comparison.

**Signature:** `def first_spike(values: list[float], window: int, factor: float) -> int | None`

**Example:** `first_spike([2.0, 2.0, 4.0, 9.0], 2, 2.0)` → `3` (index 2 equals its threshold; index 3 exceeds `2 × 3.0`).

**Watch out:** `factor` must be positive; zero or negative raises `ValueError`, even for empty input. Positive factors below one are valid. Fewer than `window + 1` readings returns `None`. Compare before sliding the previous-window total. Zero and negative means use the same signed formula: do not take absolute values or divide by the mean. This is a simple threshold exercise, not a statistical detector.

**Reread:** *A Common-Sense Guide to DSA*, Big O chapters: eliminating repeated work; `collections.deque` docs for the idea of items entering and leaving a queue (a deque is optional here).

### E4 — Clean the instrument list (easy, ~6 min)

**Goal:** **Deduplicate** means remove repeated items. Return only the first occurrence of each serial number, in its original order, using a set for O(n) average total work.

**Signature:** `def dedupe_keep_order(serials: list[str]) -> list[str]`

**Example:** `dedupe_keep_order(["PSU-7", "DMM-2", "PSU-7", "PSU-8"])` → `["PSU-7", "DMM-2", "PSU-8"]`

**Watch out:** Compare exact strings: `"PSU-7"`, `"psu-7"` and `" PSU-7 "` are different. An empty string is also a valid value. Do not sort or trim. Empty input returns `[]`. A set alone does not express the required first-seen order; keep the result in a list.

**Reread:** *A Common-Sense Guide to DSA*, Big O chapters: linear scans and how repeating a search changes the total work.
