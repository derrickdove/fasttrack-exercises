# d03 — Channels and readings: collections

**Time:** about 45 minutes · **Read first:** [Python Tutorial §5: Data Structures](https://docs.python.org/3/tutorial/datastructures.html) (lists, tuples, sets, dictionaries); *A Common-Sense Guide to Data Structures and Algorithms*, your book's chapter on hash tables (why dict or set lookup is fast and list search is slow); [The Linux Command Line, ch. 6: Redirection](https://linuxcommand.org/tlcl.php) (redirection and pipes) · **You edit:** `starter/channels.py`

## What you're building

A test station is a computer and instruments used to check hardware. A channel is a named measurement source, such as `BUS_V` for supply voltage; a reading pairs that name with a measured number. You will organize readings, summarize each channel, find missing channels, and flag repeated hardware serial numbers before a test starts.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/channels.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d03** (or run `bash tools/run.sh d03` / `tools\run.ps1 d03` from the repo root). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **collection** holds multiple items:

- A **list** keeps items in order and can change; duplicates (repeated items) are allowed.
- A **tuple** keeps a fixed sequence of items, such as a channel name and its value.
- A **dictionary** (`dict`) maps a unique **key** (here, a channel name) to a **value** (here, its list of readings).
- A **set** stores unique items and supports fast **membership** checks: asking whether an item is present with `in`.
- A **hash table** is the storage technique behind dicts and sets. Lookup usually takes about the same work as the collection grows; searching a list may inspect every item.

```python
step = ("power_on", 0.8)  # a step name and elapsed seconds
steps = [step, ("self_check", 1.2)]
durations = {name: seconds for name, seconds in steps}
finished = set(durations)
print("power_on" in finished)  # True
```

The type hints use `str` for text and `float` for measured numbers; `->` names the return type. All inputs satisfy the stated types. Reading values are finite numbers of ordinary measurement size; you do not need to validate malformed inputs. Each function returns a new collection without changing its input lists. Channel names match exactly, including capitalization and spaces, except for E4's explicit serial-number rule. Dictionary key order is not checked.

From the Linux reading: **redirection** sends a program's output to a file (`>`), and a **pipe** sends it into another program (`|`). These let an operator save or filter station reports. Today's functions work on supplied Python collections; no shell commands are required.

## Exercises

### E1 — Group station readings (easy, ~9 min)

**Goal:** Return a dictionary mapping each channel to all its values, in the order those values appeared in the input. The input is a list of `(channel, value)` tuples. Include repeated values and every channel that appears.

**Signature:** `def group_by_channel(readings: list[tuple[str, float]]) -> dict[str, list[float]]`

**Example:** `group_by_channel([("BUS_V", 28.0), ("TEMP_C", 21.0), ("BUS_V", 27.9)])` → `{"BUS_V": [28.0, 27.9], "TEMP_C": [21.0]}`

**Watch out:** Empty input returns `{}`. Each channel needs its own list; values must not leak into another channel's list. `BUS_V` and `bus_v` are different channels.

**Reread:** Python Tutorial §5.1, More on Lists; §5.3, Tuples and Sequences; §5.5, Dictionaries.

### E2 — Summarize each channel (easy–medium, ~11 min)

**Goal:** Return each channel's `(minimum, maximum, mean)` tuple. Minimum and maximum are its smallest and largest values. The arithmetic **mean** is the sum of all that channel's values divided by their count. Every reading contributes, including repeated values. You may reuse E1.

**Signature:** `def channel_stats(readings: list[tuple[str, float]]) -> dict[str, tuple[float, float, float]]`

**Example:** `channel_stats([("BUS_V", 27.0), ("TEMP_C", 20.0), ("BUS_V", 29.0)])` → `{"BUS_V": (27.0, 29.0, 28.0), "TEMP_C": (20.0, 20.0, 20.0)}`

**Watch out:** Empty input returns `{}`. One reading supplies all three numbers. Negative and zero readings are valid. Do not round the mean; tests allow tiny floating-point calculation differences. Return tuples, not lists.

**Reread:** Python Tutorial §5.3, Tuples and Sequences; §5.5, Dictionaries; §5.6, Looping Techniques.

### E3 — Find missing channels quickly (medium, ~13 min)

**Goal:** `expected` lists channel names the station requires; `seen` lists names it measured. Return each expected name absent from `seen` exactly once, sorted in Python's normal string order (`sorted`), which compares text character by character. Ignore extra names in `seen`.

**Signature:** `def missing_channels(expected: list[str], seen: list[str]) -> list[str]`

**Example:** `missing_channels(["TEMP_C", "BUS_V", "CURR_A", "TEMP_C"], ["BUS_V", "BUS_V", "AUX_V"])` → `["CURR_A", "TEMP_C"]`

**Watch out:** Duplicates in either input do not duplicate the output. Empty `expected` returns `[]`; empty `seen` returns the sorted unique expected names. Names remain case-sensitive. `test_e3_fast_enough` gives both inputs 200,000 names and allows 2 seconds for the function call. Build sets once; searching a long list separately for each expected name will be too slow.

**Reread:** Python Tutorial §5.4, Sets; §5.5, Dictionaries; your *Common-Sense Guide to DSA* chapter on hash tables, especially membership lookup versus list search.

### E4 — Flag repeated hardware serials (medium, ~12 min)

**Goal:** A **serial number** is a text identifier assigned to a piece of hardware. A **duplicate** is a later occurrence of an identifier already seen. Treat serials as case-insensitive: convert them with `str.upper()` before comparison. Return a list of upper-case serials that occur at least twice, each exactly once, ordered by when its second occurrence appears while reading left to right.

**Signature:** `def duplicate_serials(serials: list[str]) -> list[str]`

**Example:** `duplicate_serials(["a-1", "b-2", "B-2", "A-1", "b-2"])` → `["B-2", "A-1"]`

**Watch out:** Order follows the second occurrence, not the first occurrence or alphabetical order. Third and later occurrences add nothing. Inputs use letters A–Z and a–z, digits, spaces, and hyphens; keep spaces and hyphens exactly as supplied. Empty input or all-unique input returns `[]`. Do not sort or change the input.

**Reread:** Python Tutorial §5.1, More on Lists; §5.4, Sets; your book's hash-table chapter on keeping track of keys already seen.
