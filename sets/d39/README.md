# d39 — Test sequences as state machines

**Time:** about 45 minutes · **Read first:** [Wikipedia: Finite-state machine (overview)](https://en.wikipedia.org/wiki/Finite-state_machine); *A Common-Sense Guide to Data Structures and Algorithms*, chapter on graphs; [Pro Git 6.2: Contributing to a Project (forks, pull requests, review)](https://git-scm.com/book/en/v2/GitHub-Contributing-to-a-Project) · **You edit:** `starter/sequencer.py`

## What you're building

A chassis test station must prepare its instruments before taking measurements and release them even when a measurement fails. Build a sequencer: code that controls the order of a test sequence and records its progress for the operator. These exercises use local functions to stand in for instrument operations; no hardware is needed.

## How this works

1. Fill in `TRANSITIONS` and replace the `raise NotImplementedError(...)` lines in `starter/sequencer.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d39** (or run `bash tools/run.sh d39` / `tools\run.ps1 d39`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **finite-state machine** allows only specified changes between a fixed collection of states. A **state** names the current phase; a **transition** is an allowed change. A **terminal state** ends the sequence and has no outgoing transitions.

A **directed graph** represents states as nodes (points) and transitions as edges (one-way arrows). Here a **transition table** is a dictionary mapping each state to a set of allowed next states. A **set** stores distinct values; `in` checks membership. An empty set is `set()`, whereas `{}` is an empty dictionary.

```python
# A separate example: an operator station's door indicator.
allowed = {"CLOSED": {"OPEN"}, "OPEN": {"CLOSED"}}
current = "CLOSED"
target = "OPEN"
print(target in allowed.get(current, set()))  # True
```

A **callback** is a function passed to other code to call later. `Callable[[], None]` means a function taking no arguments and returning `None`; `Callable[[], bool]` returns `True` or `False`. The supplied `Setup`, `Run`, `Teardown`, and `Step` names are **type aliases**: short names for these types. A step is a tuple `(setup, run, teardown)`; a tuple groups values in a fixed order. **Teardown** means releasing resources or leaving equipment safe. **History** here is a list of visited state names, not a log of callback names.

An **exception** signals a failed operation. `try` runs protected code, `except` handles a specified exception, and `finally` runs cleanup even when the protected code fails. `ValueError` reports an invalid value; ordinary operation failures derive from `Exception`. `KeyboardInterrupt` models an operator pressing Ctrl+C and needs a separate handler because it does not derive from `Exception`. A **stack** keeps the last item added available first: `append()` adds a teardown and `reversed()` visits the saved teardowns from last to first.

## Exercises

### E1 — Allow only safe station transitions (easy, ~8 min)

**Goal:** Fill `TRANSITIONS: dict[str, set[str]]` with exactly the seven uppercase states below, then implement `can_move(a: str, b: str) -> bool` using it.

| Current state | Allowed next states |
| --- | --- |
| `IDLE` | `SETUP`, `ERROR`, `ABORTED` |
| `SETUP` | `RUNNING`, `ERROR`, `ABORTED` |
| `RUNNING` | `PASS`, `FAIL`, `ERROR`, `ABORTED` |
| `PASS`, `FAIL`, `ERROR`, `ABORTED` (each has its own dictionary entry) | none |

`IDLE` means no sequence has started; `SETUP` prepares instruments; `RUNNING` takes measurements. `PASS` means every measurement passed, `FAIL` means a measurement was outside its required limits, `ERROR` means an operation failed unexpectedly, and `ABORTED` means the operator interrupted it.

**Example:** `can_move("SETUP", "RUNNING")` → `True`; `can_move("PASS", "ERROR")` → `False`.

**Watch out:** Unknown names, lowercase names, and moves to the same state return `False`. Do not change the table while answering a query. All four terminal states have empty sets, so even emergency moves are forbidden from them.

**Reread:** Wikipedia, opening overview and Concepts and terminology; the DSA book's graphs chapter, directed graphs and storing graph connections.

### E2 — Record the instrument sequence (easy, ~9 min)

**Goal:** Implement `Sequencer.__init__(self) -> None` and `Sequencer.move(self, to: str) -> None`.

A new sequencer exposes `state == "IDLE"` and `history == ["IDLE"]`. For a move allowed by E1, update `state`, append the new state once to `history`, and return `None`. For every illegal move, raise `ValueError` and leave both attributes unchanged. No exact exception message is required. Each instance owns its own history list.

**Example:** After `station = Sequencer(); station.move("SETUP")`, its history is `["IDLE", "SETUP"]`. Asking it to move straight to `PASS` raises `ValueError`.

**Watch out:** A rejected move does not count as a visit. A terminal state cannot be restarted. Reuse `can_move` for the transition rule.

**Reread:** Wikipedia, Concepts and terminology (current state and transitions); Pro Git 6.2, GitHub Flow (review the small change to the transition rule before merging).

### E3 — Run measurements and release instruments (medium, ~17 min)

**Goal:** Implement `run_steps(steps: list[Step]) -> tuple[str, list[str]]`. Use a fresh `Sequencer` for each call. Return its final state and history. E4 extends this same function.

Follow this order exactly:

1. Move to `SETUP`. Call every setup in input order. Save each step's teardown **before** calling its setup, so even a setup that fails partway gets cleanup. Do not register or call later steps after a failure.
2. Only when every setup succeeds, move to `RUNNING` and call the run callbacks in input order. A run returning `True` passes that step; `False` selects `FAIL` and stops further runs. If all runs return `True`, select `PASS`.
3. An ordinary `Exception` from setup or run selects `ERROR` and stops further setup/run calls; it does not escape the function. Skip all runs if setup failed. A failed measurement (`False`) is different from an operation exception (`ERROR`).
4. Always call every registered teardown once in reverse registration order. This includes steps whose setup succeeded but whose run was skipped. E3 assumes teardowns succeed; E4 adds cleanup failure handling.
5. After cleanup, move once to the selected terminal state and return `(state, history)`. Do not record a terminal state before cleanup.

**Example:** Two passing steps call `setup1, setup2, run1, run2, teardown2, teardown1` and return `("PASS", ["IDLE", "SETUP", "RUNNING", "PASS"])`. Empty input follows that same state history and returns `PASS` without callbacks. A setup exception returns `("ERROR", ["IDLE", "SETUP", "ERROR"])`.

**Watch out:** Setup and teardown return `None`; run returns a Boolean. Inputs obey these types; you do not need to validate callback types or handle `SystemExit` or other exceptions outside `Exception` and `KeyboardInterrupt`. Do not alter the input list. The history contains phase transitions once each, not one entry per step. A cleanup stack and `try`/`except`/`finally` keep the code small.

**Reread:** Wikipedia, opening overview (states and inputs); the DSA book's graphs chapter (following directed edges through the phase graph).

### E4 — Handle operator aborts and cleanup failures (medium, ~11 min)

**Goal:** Extend `run_steps` with these two rules; keep E3 working.

- A `KeyboardInterrupt` from any setup or run selects `ABORTED`, stops further setup/run calls, and still runs all registered teardowns in reverse order.
- An `Exception` **or** `KeyboardInterrupt` from a teardown selects `ERROR`. Continue attempting the remaining teardowns. Cleanup failure takes priority over `PASS`, `FAIL`, `ERROR`, or `ABORTED` selected earlier. Do not let these exceptions escape.

**Example:** A run interrupted by Ctrl+C, followed by successful cleanup, returns `("ABORTED", ["IDLE", "SETUP", "RUNNING", "ABORTED"])`. If cleanup also fails, return `("ERROR", ["IDLE", "SETUP", "RUNNING", "ERROR"])` instead.

**Watch out:** Hold the selected result until cleanup finishes: moving to `ABORTED` and then to `ERROR` would violate E1. If setup was interrupted, history has no `RUNNING` entry. Teardown interruption is an equipment cleanup failure and therefore ends in `ERROR`.

**Reread:** Wikipedia, Concepts and terminology (terminal states and transitions); Pro Git 6.2, GitHub Flow and Pull Requests (review the abort and cleanup cases as part of the change).
