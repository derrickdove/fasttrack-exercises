# d15 — Practical speed: big-O on sensor data

**Time:** about 50 minutes · **Read first:** *A Common-Sense Guide to DSA*, the first chapters on Big O and the chapters on stacks and queues (your book; skip the end-of-chapter exercises because this set is today's practice); [Python `collections.deque` documentation](https://docs.python.org/3/library/collections.html#collections.deque); Python glossary entries "CPython" and "bytecode", and Python Design FAQ, "How are dictionaries implemented in CPython?" (for E5) · **You edit:** `starter/windows.py`

## What you're building

A chassis test station records thousands of sensor readings each second. Build helpers that smooth those readings, show the largest recent reading, flag sudden increases, and remove repeated instrument serial numbers before an operator sees the report.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/windows.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d15** (or run `bash tools/run.sh d15` / `tools\run.ps1 d15`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

Allow about 2 minutes of E1's estimate to read these shared rules, then start coding.

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

## Exercises

### E1 — Smooth a sensor trace (easy, ~12 min)

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

### E5 — Explain speed and the worst case (QUIZ, easy, ~5 min)

**Goal:** Explain a station's language choice and how much work a **lookup** (finding the value for a key) might need. Return a **dictionary** (or **dict**, a collection of keys paired with values) mapping exactly `"Q1"`, `"Q2"`, `"Q3"`, and `"Q4"` to your chosen uppercase option letters (`"A"`, `"B"`, `"C"`, or `"D"`). Each question has one correct option; return letters, not option text.

**Signature:** `def speed_answers() -> dict[str, str]`

**Example:** `sorted(speed_answers())` → `['Q1', 'Q2', 'Q3', 'Q4']`. This lists the question ids without showing your answer letters.

Vocabulary for these questions:

- **C** is a programming language whose variables have types declared before execution. **CPython** is the usual implementation (the program that runs the language) of Python.
- **Compile** means translate code into another code form; a **compiler** performs that translation. **Machine code** consists of instructions the processor executes directly. **Bytecode** is an intermediate instruction format; an **interpreter** is a program that executes such instructions.
- A **boxed object** stores a value together with information such as its type. A **dynamic type check** checks the actual types of values while a program runs to decide whether and how an operation is supported.
- **I/O** means input/output: exchanging data with instruments, files, or networks. **I/O-bound** work spends most of its time waiting for those exchanges. **Developer time** is time spent writing, testing, and maintaining the station software.
- **Worst-case** work is the largest amount of work for any allowed input of size `n`. **Average-case** work is the expected amount under a stated distribution (how likely different inputs are); a measured average over past runs need not describe all future inputs. Big O can describe either case; say which one you mean.
- A **hash** is a number calculated from a key to help locate its entry in a **hash table** (the storage structure a dict uses to organize entries by hash); a **collision** occurs when different keys have the same hash. In Q4, `n` is the number of stored entries; assume hashing a key and comparing two keys each take O(1) work.

**Q1.** A station sums the same readings with the same loop steps in C (with compiler settings that improve the generated code) and in CPython using ordinary Python numeric objects, with no instrument waits or calls to a library that runs the loop in C. Why does the C loop usually run much faster?

- A. CPython runs the source text from scratch on every iteration; it never uses bytecode.
- B. C is compiled to machine code; CPython interprets bytecode and handles boxed objects and dynamic type checks, adding work per iteration.
- C. C's speed means its linear loop has become O(1), while the Python loop remains O(n).
- D. CPython and C execute the same machine instructions for this loop; the difference comes only from loading the file.

<details>
<summary>Why it matters on the job — Q1</summary>

Explaining a slow sensor calculation helps the team choose which change to investigate.

</details>

**Q2.** A station script spends almost all its time waiting for instrument replies, and its calculations already meet the required response time. Which language-choice argument best fits this situation?

- A. Rewrite in C because faster arithmetic will remove the instrument's reply delay.
- B. Rewrite in C because an I/O-bound program cannot meet timing requirements in Python.
- C. Keep Python because it always performs arithmetic faster than C with compiler improvements enabled.
- D. Keep Python because instrument waits dominate and developer time matters; a faster loop may make little difference to the whole step.

<details>
<summary>Why it matters on the job — Q2</summary>

Station software must balance test duration with the effort needed to maintain reliable instrument control.

</details>

**Q3.** A search stops at the first out-of-limit reading in a list of `n` readings; historical runs usually stop early, but an allowed input can have every reading in limits. Which statement correctly separates the observed average from worst-case work?

- A. The worst case is O(n), because every reading may need checking; a small historical average does not guarantee constant work for every input.
- B. The worst case is O(1), because most historical runs stopped after a few readings.
- C. The average must be O(1) for every possible input distribution, because the search has an early return.
- D. The worst case is O(n × n), because both the list length and the stopping position can grow.

<details>
<summary>Why it matters on the job — Q3</summary>

A test step's response requirement applies to allowed measurement traces beyond the ones already recorded.

</details>

**Q4.** A station uses a dict to look up instrument settings by serial number. With well-distributed hashes for the average case, but allowing severe collisions in the worst case, what is the work for one lookup under the vocabulary's assumptions about hashing and comparing keys?

- A. Average O(n), worst O(1).
- B. Average O(1), worst O(1), because hashing prevents collisions.
- C. Average O(1), worst O(n).
- D. Average O(n), worst O(n), because every lookup scans every stored key.

<details>
<summary>Why it matters on the job — Q4</summary>

An instrument registry needs a clear performance claim as the number of connected devices grows.

</details>

**Watch out:** Return answers without measuring execution speed, connecting to instruments, or compiling C. Quiz failures name the question and a reading to revisit; they do not supply the correct option letter.

**Reread:** Python glossary, "CPython" and "bytecode" (Q1); the I/O and developer-time vocabulary above (Q2); *A Common-Sense Guide to DSA*, Big O chapters on counting work for different inputs (Q3); Python Design FAQ, "How are dictionaries implemented in CPython?" and the book's hash-table lookup discussion (Q4).
