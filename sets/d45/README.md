# d45 -- Multi-instrument, multi-UUT configuration

**Time:** about 65 minutes | **Read first:** Python's [tomllib documentation](https://docs.python.org/3/library/tomllib.html) (load and Examples); *A Common-Sense Guide to DSA*, your book's chapter on graphs (topological ordering and breadth-first search); [Pro Git 7.6: Rewriting History](https://git-scm.com/book/en/v2/Git-Tools-Rewriting-History) (when not to rewrite shared history) | **You edit:** `starter/topology.py`

## What you're building

A **test station** controls measuring equipment while testing several chassis. A **UUT** (unit under test) is one chassis; an **instrument** is a controlled piece of equipment. You will check station wiring, order instrument setup, and find scheduled tests that compete for the same instrument.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/topology.py`. Don't edit `tests/` or the supplied `UUT_INSTRUMENTS` mapping.
2. Press **Ctrl+Shift+B -> Test: d45** (or run `bash tools/run.sh d45` / `tools\run.ps1 d45`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **configuration** is data describing station connections. **TOML** is a text format for that data; `tomllib` is Python's built-in TOML reader. `[[instruments]]` introduces another dictionary in the `instruments` list. A **resource** is a string identifying a reservable connection, including the channel when needed. An **id** is a string naming a record. A **PSU** (power supply unit) provides electrical power; a **channel** is an independently controlled output. A **DMM** (digital multimeter) measures electrical values; a **scope** (oscilloscope) measures signals over time.

A **graph** represents things as nodes and relationships as edges. Here, nodes are instrument ids and an edge says that one instrument needs another ready first. A **prerequisite** must be ready before the instrument that needs it. A **topological order** puts every prerequisite before anything needing it. A **cycle** is a closed chain of prerequisites, so setup cannot finish. **Kahn's algorithm** repeatedly removes a ready node (one with no unmet prerequisites). A **min-heap**, supplied by `heapq`, keeps the alphabetically smallest ready id available without sorting the whole queue each time.

A **half-open window** `[start, end)` includes its start and excludes its end. A **sweep** visits windows in start-time order and remembers the ends of earlier windows. A Python **set** removes duplicates; `sorted(...)` turns it into an ordered list:

```python
reserved = {"scope", "meter", "scope"}
print(sorted(reserved))  # ["meter", "scope"]
window = ("rack-left", 5, 9)
uut, start, end = window  # unpack a tuple into three names
```

Configuration changes are reviewed with station code. **Shared history** means Git commits other people may already use. Pro Git's rule applies here: avoid rewriting those commits; make a new corrective commit. No Git commands are required in this set.

## Exercises

### E1 -- Read and check station wiring (easy, ~13 min)

**Goal:** Load TOML and report all wiring problems together.

**Signatures:** `load(path: str | Path) -> dict[str, Any]` and `validate(cfg: dict[str, Any]) -> list[str]`. `Any` allows the nested dictionaries and lists returned by TOML. `Path` is `pathlib.Path`, Python's portable filesystem path type.

`load` accepts a string path or `Path`. Open it in binary mode (`"rb"`) and use `tomllib.load`. Return its dictionary unchanged; do not validate it or change module state. Let `FileNotFoundError` and `tomllib.TOMLDecodeError` escape to the caller. An empty TOML file returns `{}`.

`data/station.toml` is a valid example. `validate` receives an already parsed dictionary. Its supported **schema** (the shape of the data) is:

- `instruments`: list of dictionaries with nonempty string fields `id`, `kind`, and `resource`. `kind` is `psu`, `dmm`, or `scope`. Each `psu` record represents one channel, so channels on the same box need different ids and resources.
- `uuts`: list of dictionaries with a nonempty string `id` and an `instruments` list of instrument-id strings. An empty list is allowed. Repeated references within one UUT are allowed.
- Either top-level list may be absent; treat it as empty. Ignore other fields. Field types and required fields within each record are guaranteed; you do not need general schema checking.

Return the following exact messages for each problem, sorted alphabetically with duplicates removed:

| Problem | Message format |
| --- | --- |
| Repeated instrument id | `duplicate instrument id: ID` |
| Repeated UUT id | `duplicate uut id: ID` |
| Repeated resource, even for different instrument ids | `duplicate resource: RESOURCE` |
| UUT refers to an instrument id that does not exist | `unknown instrument: UUT -> INSTRUMENT` |
| Two or more distinct UUT ids reference one PSU channel | `shared psu channel: INSTRUMENT -> UUT1, UUT2` |

For shared-channel messages, list all distinct UUT ids alphabetically, separated by comma-space. Sharing a DMM or scope is allowed in the wiring; E4 checks when it is used. Instrument ids and UUT ids have separate namespaces: the same spelling in each list is allowed. Compare all strings exactly, including case. If an instrument id repeats, use its first record's `kind` for PSU checks, but still inspect every record for repeated resources. Inspect every UUT record, even if its id repeats. Do not modify `cfg`.

**Example:** adding `"psu-a"` to `uut-b` in the supplied configuration makes `validate(cfg)` return `["shared psu channel: psu-a -> uut-a, uut-b"]`. Valid wiring returns `[]`.

**Watch out:** Return all problems in one call. Different channels on one PSU are allowed; two UUTs owning the same channel are unsafe here.

**Reread:** `tomllib`: load and Examples; Pro Git 7.6: the warnings about changing commits others have used.

### E2 -- Find one chassis's instruments (easy, ~5 min)

**Goal:** Give the operator a predictable list of the instrument ids used by a UUT.

**Signature:** `instruments_for(cfg: dict[str, Any], uut_id: str) -> list[str]`

Assume `cfg` satisfies E1's schema and has no validation errors. Return a new, alphabetically sorted list of that UUT's instrument ids, with duplicates removed. A UUT with no instruments returns `[]`. If the UUT is absent, raise `KeyError(uut_id)`, including for an empty configuration. Leave `cfg` unchanged; do not call `load` or use `UUT_INSTRUMENTS` here.

**Example:** `instruments_for(cfg, "uut-a")` for the supplied TOML -> `["dmm", "psu-a"]`.

**Watch out:** An existing UUT with no instruments differs from an unknown UUT.

**Reread:** `tomllib`: Examples (the dictionaries and lists returned by parsing); your book's graphs chapter: representing connections.

### E3 -- Set up instruments in dependency order (medium, ~14 min)

**Goal:** Build a safe startup order. A **dependency** is a prerequisite: in `deps["scope"] = ["trigger"]`, the trigger must be ready before the scope.

**Signature:** `setup_order(deps: dict[str, list[str]]) -> list[str]`

Include every id appearing as a key or in a value list, exactly once. An id appearing only in a value has no prerequisites. Treat repeated prerequisites as one edge. Use Kahn's algorithm. At every step choose the alphabetically smallest id among **all currently ready ids**, including newly ready ones. Empty input returns `[]`. Leave the input unchanged.

If there is a cycle, raise `ValueError` with `cycle: ` followed by one actual closed dependency path separated by ` -> `, for example `cycle: psu -> relay -> psu`. Each id in this error depends on the next, and the last repeats the first. Any real cycle is accepted; omit downstream nodes that are merely blocked by it. For the same input, report the same path each time. A node depending on itself is a cycle too.

**Example:** `setup_order({"scope": ["trigger"], "dmm": []})` -> `["dmm", "trigger", "scope"]`.

**Watch out:** If `a` becomes ready after `b`, choose `a` before an already waiting `z`. Sorting once at the beginning is insufficient. To name a cycle after Kahn stops, follow unmet prerequisites until an id repeats; keep only that closed part of the walk.

**Reread:** your book's graphs chapter: directed edges, cycles, and topological ordering.

### E4 -- Detect competing test windows (medium, ~13 min)

**Goal:** Find distinct chassis that need the same instrument at the same time.

**Signature:** `conflicts(schedule: list[tuple[str, int, int]]) -> list[tuple[str, str]]`

E4 uses the supplied `UUT_INSTRUMENTS` mapping in `topology.py`, matching the example station. It is available immediately: no earlier function call configures E4. `uut-a` and `uut-b` share `dmm`; `uut-c` uses only `scope`; `uut-d` shares `dmm` and `scope`. All listed instruments are occupied for the full window. E4 treats each instrument id as a resource, regardless of its kind.

Each tuple contains `(uut_id, start, end)` with integer station-clock times in seconds. Negative times are allowed; every window must have `start < end`. Raise `KeyError(uut_id)` for an unknown UUT or `ValueError("invalid window: UUT")` for a reversed or zero-length window. Check records in input order, checking the id before the times in each record.

Two windows overlap when `max(start1, start2) < min(end1, end2)`. Touching endpoints do not overlap. Report a pair only for **different UUT ids** with at least one shared instrument and at least one overlapping pair of windows. A UUT may occur many times, including overlapping windows of its own. Report each UUT pair once, even if several windows or instruments conflict. Put the smaller id first within each tuple, then sort the result list alphabetically. Empty input returns `[]`. Do not modify the schedule or supplied mapping.

**Example:** `conflicts([("uut-b", 2, 6), ("uut-a", 0, 3), ("uut-c", 1, 9)])` -> `[("uut-a", "uut-b")]`.

**Watch out:** Use sort + sweep, not all pairs of windows. For this fixed four-UUT station, remember the latest end seen for each UUT. At each start, compare with the other three UUTs; an earlier end greater than this start means overlap. Keep the maximum end when the same UUT appears again. **Big O** describes how work grows with input size. This takes O(n log n) time (sorting dominates as the number `n` of windows grows), while testing every pair takes O(n^2). The speed test gives 80,000 windows a generous 2-second limit; its input is reversed rather than random so every run is reproducible.

**Reread:** your book's graphs chapter: nodes and connections; here shared instruments connect UUTs, and the sweep checks when those connections cause contention (simultaneous demand).

### E5 -- Count clusters of failed test points (medium, ~20 min)

**Goal:** A **harness** is an assembly of wires and connectors; a **pin** is one electrical contact in a connector. A harness test reports a **grid**, a rectangular arrangement of pin results stored as a list of row strings. `"X"` marks a failed pin and `"."` marks a passed pin. Count groups of failures that may share one physical fault, and find the biggest group.

**Signatures:** `count_fault_clusters(grid: list[str]) -> int` and `largest_cluster(grid: list[str]) -> int`

A **cluster** contains failed pins connected by steps up, down, left, or right through other failed pins. Diagonal contact does not connect pins. `count_fault_clusters` returns the number of clusters; `largest_cluster` returns the number of pins in the biggest cluster. Both return `0` when there are no failed pins, including an empty list or equal-length empty rows. Both must raise `ValueError` if rows have different lengths or any character is other than uppercase `X` or `.`. Check the whole grid, including later rows. Leave the input unchanged, and keep separate calls independent.

Here the graph's nodes are failed pins and its edges join side-by-side failures. **Breadth-first search (BFS)** explores one starting pin's neighbours, then their neighbours, until it has found the whole cluster. Use a **queue**, which processes items in the order they were added, and a **visited set**, which remembers pins already discovered. Identify a pin by its **coordinates**, a `(row, column)` tuple of zero-based positions (the first row and column are numbered `0`).

Python's standard-library `collections.deque` is a **double-ended queue**: it supports fast removal and insertion at either end. `append` adds to the right; `popleft` removes and returns the oldest item on the left. This small example shows the queue operations, using pin names instead of coordinates:

```python
from collections import deque
pending = deque(["pin-1", "pin-2"])
visited = {"pin-1", "pin-2"}
pending.append("pin-3")
visited.add("pin-3")
print(pending.popleft())  # pin-1
```

Scan the grid for an `X` that is not visited. That starts a new cluster: add it to the queue and visited set. Repeatedly remove a queued pin, count it, and add its valid, unvisited failed neighbours. Mark a pin visited when you add it to the queue, so two neighbours cannot add it twice. When the queue is empty, you know that cluster's size. Continue the scan, keeping the visited set across clusters and remembering the largest size. A shared helper for the two functions is allowed.

**Example:** These are separate calls on the same grid:

| `grid` | `count_fault_clusters(grid)` | `largest_cluster(grid)` |
| --- | --- | --- |
| `['XX..X', '.X..X', '...X.']` | `3` | `3` |
| `['X.', '.X']` | `2` | `1` |
| `['XXX', 'X.X', 'XXX']` | `1` | `8` |
| `['....', '....']` | `0` | `0` |
| `[]` | `0` | `0` |

**Watch out:** Check row and column bounds before indexing: negative indexes in Python wrap around to the end and would incorrectly join opposite grid edges. Passed pins never join clusters. Each function must handle a 1000-by-1000 grid of all `X` in under 3 seconds: one cluster containing 1,000,000 pins. Visit each pin at most once during the search. A **recursive** function calls itself; Python limits how many such calls can be nested. A recursive search can hit that recursion limit and raise `RecursionError` on a large grid. Use the queue and a loop instead.

**Reread:** your book's graphs chapter: breadth-first search, its queue, and keeping track of visited nodes.
