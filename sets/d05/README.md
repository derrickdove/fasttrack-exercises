# d05 — When things go wrong: exceptions

**Time:** about 45 minutes · **Read first:** [Python Tutorial §8: Errors and Exceptions](https://docs.python.org/3/tutorial/errors.html); Pro Git [2.3: Viewing the Commit History](https://git-scm.com/book/en/v2/Git-Basics-Viewing-the-Commit-History) and [2.4: Undoing Things](https://git-scm.com/book/en/v2/Git-Basics-Undoing-Things). The set specification also names *The Pragmatic Programmer*, topic "Dead Programs Tell No Lies", as companion reading. · **You edit:** `starter/errors.py`

## What you're building

A chassis test station controls instruments that measure electrical signals. An instrument may report a bad command or stop answering; your code will preserve those failures, empty its stored errors, and retry a measurement only when a timeout makes retrying appropriate. All instrument calls here are supplied Python functions, so you need no hardware.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/errors.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d05** (or run `bash tools/run.sh d05` / `tools\run.ps1 d05`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise; E3 uses E2, and E4 uses E1.
3. Report **all pass / partial / stuck** in the tracker.

An **exception** is an object describing a failure; `raise` stops normal execution and sends it to a matching `except` block.
A **custom exception** is your own class derived from `Exception`; `__init__` initializes an object, and `__str__` supplies its text for `str(error)`.
An **attribute** is a value stored on an object, such as `error.message`; `super().__init__(...)` initializes the parent exception, whose `.args` tuple stores those arguments.
A **tuple** is an ordered group of values; `(code, message)` keeps a numeric code beside its text.
A **callable** is something you can call like a function; `Callable[[str], str]` accepts one string and returns a string, while `Callable[[], float]` takes no arguments and returns a number.
A **timeout** means an operation did not answer within its allowed time; a **retry** is another attempt after failure.
To **propagate** an exception is to let it reach the caller; bare `raise` inside `except` re-raises the same exception object.

```python
try:
    voltage = float("disconnected")
except ValueError as error:
    print(f"Invalid voltage: {error}")
```

This catches `ValueError`, Python's exception for an unacceptable value. Exceptions of other types still propagate. In the Pro Git reading, **history** means recorded commits (saved versions), and **undoing** means restoring an earlier state; use that reading to inspect your edits before choosing what to restore.

## Exercises

### E1 — Give instrument failures useful details (easy, ~9 min)

**Goal:** Define two exception types so a station can distinguish an unanswered measurement from an error reported by the instrument.

**Signatures:** `InstrumentTimeout(message: str)` and `InstrumentError(code: int, message: str)`, both direct subclasses of `Exception`; implement their supplied `__init__` and `__str__` methods.

**Contract:** A timeout stores `message` unchanged, returns that message from `str()`, and initializes its parent with `message` (`.args == (message,)`). An instrument error stores `code` and `message` unchanged and initializes its parent with both (`.args == (code, message)`). Its string is exactly `instrument error <code>: <message>`. No validation is needed; codes may be negative, zero, or positive, and messages may be empty.

**Example:** `str(InstrumentError(-113, "Undefined header"))` → `"instrument error -113: Undefined header"`; `str(InstrumentTimeout("CH1 did not answer"))` → `"CH1 did not answer"`.

**Watch out:** Keep the numeric code as an integer. Both types must be usable with `raise` and `except`.

**Reread:** Python Tutorial §8.5, User-defined Exceptions; §8.3, Handling Exceptions.

### E2 — Read one instrument error reply (easy–medium, ~12 min)

**Goal:** Turn one text reply into a `(code, message)` tuple. The **error code** is the instrument's integer identifying a fault; code zero means no error.

**Signature:** `parse_error_reply(reply: str) -> tuple[int, str]`

**Contract:** Remove surrounding whitespace from the whole reply first. The remaining format is an optional `+` or `-`, one or more ASCII decimal digits (the characters `0` through `9`), a comma, then a double-quoted message. There are no spaces around the comma or inside the numeric code. The message may be empty and may contain commas and spaces; preserve them exactly. It cannot contain a double quote, a carriage return (`\r`), or a newline (`\n`); escaped quotes are not supported. Return the integer code and the text inside the quotes. Raise `ValueError` for every malformed string. Inputs are always strings.

**Examples:** `'-113,"Undefined header"'` → `(-113, "Undefined header")`; `'+0,"No error"'` → `(0, "No error")`; `'12,"CH1, overload"'` → `(12, "CH1, overload")`.

**Watch out:** Splitting at every comma breaks messages containing commas. Python's `int()` accepts some strings this format forbids; validate the code's characters as well as converting it. `str.partition(",")` splits only at the first comma.

**Reread:** Python Tutorial §8.2, Exceptions; §8.3, Handling Exceptions; §8.4, Raising Exceptions.

### E3 — Empty the station's stored instrument errors (medium, ~12 min)

**Goal:** Drain an instrument's **error queue**, its ordered collection of error replies waiting to be read. A **query** sends a command and returns its reply.

**Signature:** `drain_errors(query: Callable[[str], str], max_reads: int = 20) -> list[tuple[int, str]]`

**Contract:** Each read calls `query("SYST:ERR?")` exactly once; this command asks the instrument for its next error. Parse the reply with E2. Append each nonzero `(code, message)` in arrival order, including duplicate errors. At the first zero code, return the accumulated list without that zero reply, and make no further calls. A first reply of zero returns `[]`.

`max_reads` is an integer counting all reads, including the terminating zero. Zero on the final allowed read succeeds. If all allowed reads have nonzero codes, raise `RuntimeError` immediately after the last allowed read; do not return partial results or make an extra call. Reject `max_reads < 1` with `ValueError` before calling `query`. Propagate exceptions from `query` and malformed-reply `ValueError` immediately, with no extra reads. No particular exception message is required.

**Example:** Replies `'-113,"Undefined header"'`, `'+0,"No error"'` produce `[(-113, "Undefined header")]` in two calls.

**Watch out:** The default permits 20 reads, not 20 errors plus a final read. You never need a real instrument or a delay.

**Reread:** Python Tutorial §8.3, Handling Exceptions; §8.4, Raising Exceptions; §8.6, Exception Chaining (the example shows propagation with bare `raise`).

### E4 — Retry an unanswered measurement (medium, ~12 min)

**Goal:** Let a station recover from a timeout while preserving failures that retrying cannot fix.

**Signature:** `safe_measure(measure: Callable[[], float], retries: int) -> float`

**Contract:** `retries` is an integer; reject negative values with `ValueError` before calling `measure`. Call `measure()` once, then allow up to `retries` extra calls only after `InstrumentTimeout` (including subclasses). Return the first successful value unchanged, including zero or a negative value, and stop calling. With `retries=0`, there is one attempt. If every attempt times out, re-raise the **last exception object**, preserving its details. Any other exception, including `InstrumentError`, propagates immediately, even after an earlier timeout. Add no delays and do not convert exceptions to a measurement value. No particular exception message is required for invalid retries.

**Example:** With `retries=2`, a timeout followed by `3.25` returns `3.25` after two calls; three timeouts raise the third timeout object.

**Watch out:** A broad `except Exception` would retry broken commands as well as timeouts. The retry budget counts extra attempts, not total attempts.

**Reread:** Python Tutorial §8.3, Handling Exceptions (matching exception types); §8.4, Raising Exceptions (bare `raise`). Companion: *The Pragmatic Programmer*, "Dead Programs Tell No Lies".
