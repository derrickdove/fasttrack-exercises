# d27 — Telemetry reliability: gaps, duplicates and wraparound

**Time:** about 55 minutes · **Read first:** [Wikipedia: Serial number arithmetic](https://en.wikipedia.org/wiki/Serial_number_arithmetic) (overview) and [The Linux Command Line, chapter 17: Searching for Files](https://linuxcommand.org/tlcl.php) (`find`, `xargs`). Python's [`collections.deque`](https://docs.python.org/3/library/collections.html#collections.deque) is a useful lookup; [RFC 1982 §3](https://www.rfc-editor.org/rfc/rfc1982#section-3) is optional. · **You edit:** `starter/sequence.py`

## What you're building

A chassis test station receives **telemetry**, measurements sent by the hardware under test. Each **packet** (one transmitted message) has a **sequence number**, a counter that identifies its position in the stream. Build checks that distinguish lost packets, repeated packets and late arrivals, then report stream reliability to the operator.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/sequence.py`. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: d27** (or run `bash tools/run.sh d27` / `tools\run.ps1 d27`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **16-bit counter** has 65536 possible values, 0 through 65535. **Wraparound** means 65535 is followed by 0. **Serial arithmetic** compares counters on this ring rather than treating 0 as always older than 65535. `%` is the modulo operator: `65536 % 65536` is `0`.

A **gap** is a run of skipped sequence numbers. A **duplicate** repeats a number in recent arrival history. **Out of order** means a nonduplicate arrival does not advance the stream's latest forward position. A **window** is the limited history used for this decision. Assume one continuous stream with no device resets, and forward jumps smaller than half the ring (32768); larger jumps cannot be distinguished from old packets using the sequence number alone.

A **set** holds unique values and supports fast membership checks. A **dictionary** maps keys to values; here it can count how many copies of each number remain in history. A **deque** (double-ended queue) holds arrival order and can quickly remove its oldest item with `popleft()`:

```python
from collections import deque
recent_channels = deque([2, 4])
recent_channels.append(7)
oldest_channel = recent_channels.popleft()  # 2; remaining channels: 4, 7
```

Chapter 17's `find` locates files and `xargs` builds commands from input. Use those ideas when locating saved telemetry logs at a Linux station; this set tests the counter analysis in Python and requires no shell commands.

## Exercises

### E1 — Compare station packet counters (easy, ~6 min)

**Goal:** Compute `a - b` as a signed difference on the 16-bit ring.

**Signature:** `def seq_diff(a: int, b: int) -> int`

Return the unique equivalent difference in **-32768 through 32767**, inclusive. A positive result means `a` is ahead of `b`; a negative result means behind. Equal numbers return 0. At exactly half the ring, both comparison directions return **-32768**. This is this exercise's tie rule; RFC 1982 leaves the ordering at that distance undefined.

**Example:** `seq_diff(1, 65535)` → `2`; `seq_diff(65535, 1)` → `-2`.

**Watch out:** All sequence inputs throughout this set are integers. Raise `ValueError` for any outside 0..65535; do not silently normalize them. You do not need to handle other input types.

**Reread:** Wikipedia, overview and Comparison; optional RFC 1982 §3.2, Comparison.

### E2 — List packets skipped by the station (easy, ~8 min)

**Goal:** Return missing sequence numbers between two arrivals, excluding both endpoints.

**Signature:** `def missing_between(last: int, new: int) -> list[int]`

Use `seq_diff(new, last)` to decide direction. For a positive difference, return the skipped numbers in forward arrival order, wrapping through 0 when needed. Return a fresh empty list for equal values, backward steps or the half-ring tie. Validate both inputs as in E1, even when the result would be empty.

**Example:** `missing_between(65534, 2)` → `[65535, 0, 1]`; `missing_between(12, 11)` → `[]`.

**Watch out:** A consecutive arrival has no gap. The largest supported forward difference is 32767, so its gap contains 32766 numbers.

**Reread:** Wikipedia, Addition and Comparison; optional RFC 1982 §3.1, Addition.

### E3 — Keep a live gap tracker (medium, ~20 min)

**Goal:** Keep reliability state across packets arriving at a chassis test station.

**Signatures:** `class GapTracker`, `def __init__(self) -> None`, `def update(self, seq: int) -> list[int]`

Each new instance starts with public integer counters `received = 0`, `duplicates = 0`, `out_of_order = 0`, and `missing = set()`. Here `missing` is a set of still-absent sequence numbers, not a count. Keep a private latest forward position and private recent history. Each valid `update` follows these rules in order:

1. Increment `received` for **every** arrival, including duplicates and late packets.
2. Check whether `seq` occurs in the **previous 1024 arrivals** (or all previous arrivals if fewer). If yes, increment `duplicates`, return `[]`, and leave the latest position and `missing` unchanged. Check before removing the oldest history item.
3. Otherwise remove `seq` from `missing` if present. The first packet sets the latest position and returns `[]`. For later packets, compare with that latest position using E1. A positive difference advances the position, adds E2's gap to `missing`, and returns that gap. A zero or negative difference increments `out_of_order`, leaves the latest position unchanged, and returns `[]`.
4. Every valid arrival enters history, including duplicates and out-of-order packets. Retain only the latest 1024 arrivals. Repeated numbers occupy separate history positions.

Reject an invalid sequence with `ValueError` **before changing any state**. Callers only read the public attributes. Instances must have independent state.

**Example:** Updates `10, 13, 11, 13` return `[], [11, 12], [], []`. The final attributes are `received=4`, `duplicates=1`, `out_of_order=1`, `missing={12}`. A subsequent `14` returns `[]`: the late `11` did not move the latest position backward.

**Watch out:** A late packet can repair a previously detected gap. History counts arrivals, not distinct numbers. If you use a deque plus a dictionary of occurrence counts, removing one occurrence must not erase another. Avoid an ever-growing list of every arrival: long station runs must retain only bounded recent history. `missing` stores sequence values only; it does not distinguish losses with the same number on different full turns of the ring.

**Reread:** Wikipedia, Comparison and its half-range limitation; Python `collections.deque`, `append` and `popleft`.

### E4 — Summarize a telemetry run (medium, ~11 min)

**Goal:** Produce four numbers an operator can use to judge a captured stream.

**Signature:** `def loss_report(seqs: list[int]) -> dict[str, int | float]`

Process the list in its original arrival order using a fresh `GapTracker`. Return a dictionary with exactly these keys:

- `"received"`: integer number of arrivals, including duplicates (`tracker.received`).
- `"missing"`: integer size of the final still-missing set.
- `"loss_pct"`: floating-point percentage, `100.0 * missing / (received - duplicates + missing)`. Return `0.0` when the denominator is zero. Excluding duplicates prevents repeats from improving this estimate.
- `"longest_gap"`: largest number of skipped packets returned by any one `update`, or 0 if none. This is a historical maximum; late repairs do not reduce it.

**Example:** `loss_report([10, 13, 11, 13])` → `{"received": 4, "missing": 1, "loss_pct": 25.0, "longest_gap": 2}`. An empty input returns all zeros, with `loss_pct` equal to `0.0`.

**Watch out:** Do not sort or change the input list. Propagate `ValueError` for invalid numbers. Avoid rescanning the whole capture for each packet: the speed test analyzes **500,000 consecutive packets, including multiple wraps, in at most 2 seconds** (only the function call is timed). This report shares E3's sequence-value-only missing-set simplification.

**Reread:** Wikipedia, overview and Comparison; Python `collections.deque`, bounded history operations. Chapter 17's `find` and `xargs` explain how a station operator could locate captures before running this analysis.

### E5 — Count events in the last N milliseconds (medium, ~10 min)

**Goal:** The telemetry monitor records one event each time a packet is dropped. Let the operator ask how many drops occurred in the last N milliseconds. A **millisecond** (ms) is one thousandth of a second; an event's **timestamp** is the clock value when it was recorded.

**Signatures:**

```python
class EventCounter:
    def __init__(self, clock: Callable[[], int]) -> None: ...
    def record(self) -> None: ...
    def count_last(self, ms: int) -> int: ...
    def __len__(self) -> int: ...
```

A function can be passed around like any other value. A **callable** is a value you can call with parentheses; `Callable[[], int]` describes one that takes no arguments and returns an integer. Pass the function itself as `clock`, then call `clock()` whenever you need the current time. Its result is integer milliseconds and never goes backwards; you may assume this promise holds. Passing the clock in makes the class testable: tests supply a **fake clock**, a callable whose returned time they control, instead of waiting for real time to pass.

Start with no events. `record()` records one event at `clock()` and returns `None`. Many events may share the same millisecond; each counts separately. `count_last(ms)` reads the current time as `now` and returns the number of recorded events whose timestamp `t` satisfies **`now - ms <= t <= now`**, inclusive at both ends. Thus `ms=0` counts events at exactly `now`, and `ms=10_000` includes events exactly 10,000 ms old. Queries may request windows in any order and do not consume events.

Raise `ValueError` unless `ms` is an integer in **0..10_000**. Reject `True` and `False` too: Python treats booleans as integers in `isinstance(value, int)`, so that check alone is insufficient. Floats such as `5.0` and strings such as `"5"` are invalid; do not convert them.

On `record()`, a valid `count_last()`, and `len(counter)`, remove events strictly older than `now - 10_000` from a deque using `popleft()`. No allowed future query can need them. Implement `__len__` so `len(counter)` returns the number of stored events after this cleanup, even if the clock has advanced without another event. Never discard a younger event just because the current query requests a short window. Storage should depend on events in the last 10,000 ms, rather than the whole station run; this is a time limit, not a fixed limit on the number of drops. This also applies to any extra list or dictionary you keep: expired entries must be removed periodically even if your counts are already correct. Each counter has independent history.

**Example:** A fake clock lets you try exact boundaries without sleeping:

```python
now = 1_000

def fake_clock() -> int:
    return now

counter = EventCounter(fake_clock)
counter.record()
counter.record()                 # another drop at 1,000 ms
now = 1_005
counter.record()
counter.count_last(5)             # 3: includes both 1,000 and 1,005
counter.count_last(0)             # 1: only the drop at 1,005
len(counter)                     # 3
now = 11_001
counter.count_last(10_000)        # 1: the two drops at 1,000 have expired
len(counter)                     # 1
```

**Reread:** The day's serial-number arithmetic overview for the surrounding telemetry work; Python `collections.deque`, `append` and `popleft` (reread from d15).
