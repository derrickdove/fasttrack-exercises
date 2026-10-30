# d20 — Safe by default: context managers, timeouts and retries

**Time:** about 45 minutes · **Read first:** [contextlib, the with statement, and decorators](https://docs.python.org/3/library/contextlib.html), [Missing Semester: Debugging and Profiling](https://missing.csail.mit.edu/2020/debugging-profiling/), [Python Tutorial §8.7: Defining Clean-up Actions](https://docs.python.org/3/tutorial/errors.html#defining-clean-up-actions), and [functools.wraps](https://docs.python.org/3/library/functools.html#functools.wraps) · **You edit:** `starter/safety.py`

## What you're building

A test station uses a power supply unit (**PSU**) to power the hardware being tested. You will make its output cleanup reliable, retry temporary communication failures, bound readiness checks, and increase voltage gradually. Tests use supplied stand-ins for instruments and time, so no hardware is needed.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/safety.py`. Don't edit `tests/`. The supplied `Protocol` classes describe the methods an instrument must offer; their `...` declarations are complete and need no edits.
2. Press Ctrl+Shift+B → **Test: d20** (or run `bash tools/run.sh d20` / `tools\run.ps1 d20`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report all pass / partial / stuck in the tracker.

A **channel** is an independently controlled PSU output, identified here by an integer. A **context manager** runs entry and exit actions around a `with` block; Python calls `__enter__` before the block and `__exit__` when it ends, including on an exception (a raised error). Returning false from `__exit__` lets that error continue to the caller. A `finally` block runs cleanup whether a `try` block succeeds or fails.

A **decorator** wraps a function to add behavior; `@decorator` applies it. `functools.wraps` copies the original function's name and documentation onto the wrapper. `*args` and `**kwargs` forward positional and named arguments. A **callable** is something you can call, such as a function. `ParamSpec` and `TypeVar` in the supplied annotations keep argument and result types connected; you need not change those annotations.

A **retry** is another attempt after a specified error. **Polling** means checking repeatedly. A **deadline** is a time after which no further check starts; a **monotonic clock** measures elapsed time without jumping when the computer's calendar clock changes. **Injection** means passing a replacement dependency, such as a fake sleep function, to make behavior easy to test. A **truthy** result acts like true in an `if`; `False`, `None`, `0`, and empty containers are falsey.

```python
from contextlib import nullcontext

with nullcontext("station A") as name:  # a context manager with no cleanup
    print(name)
```

## Exercises

### E1 — Leave every output off (easy, ~10 min)

**Goal:** Implement `OutputGuard(psu, channels)` and its context-manager methods. `psu.output(ch, False)` disables a channel. Store a snapshot (an independent copy) of the supplied sequence of channel numbers at construction, so later changes to the caller's list do not affect cleanup. Construction and entry make no instrument calls. Entry returns the guard itself.

**Signature:** `OutputGuard(psu: OutputDevice, channels: Sequence[int])`; see the supplied `__enter__` and `__exit__` signatures.

Python passes `__exit__` the exception class (`exc_type`), the exception object (`exc_value`), and its recorded call stack (`traceback`); all three are `None` on a normal exit. On exit, attempt to disable every listed channel in order, including duplicates. An empty sequence does nothing. Return `False` when cleanup completes. If a cleanup call raises, still attempt the remaining channels. If the block already raised, preserve that same exception object; otherwise raise the first cleanup exception. This also applies to interruption exceptions such as `KeyboardInterrupt`, which inherit from `BaseException` rather than `Exception`.

**Example:** `with OutputGuard(psu, [2, 1]): ...` ends by calling `output(2, False)` then `output(1, False)`.

**Watch out:** Do not enable outputs or suppress the block's error. This guard requests shutdown; an instrument that rejects an off command cannot be guaranteed to turn off.

**Reread:** contextlib, “Examples and Recipes” → “Supporting a variable number of context managers”; Python Tutorial §8.7; Missing Semester, “Debugging” → “Logging”. Trace the order of cleanup events when debugging.

### E2 — Retry a temporary instrument failure (medium, ~12 min)

**Goal:** Implement a decorator factory (a function that returns a decorator) for station operations.

**Signature:** `retry(times: int, exceptions: tuple[type[Exception], ...], delay_s: float = 0, sleep=time.sleep)`

`times` is the total number of attempts, including the first. Reject `times < 1` or `delay_s < 0` with `ValueError` when `retry(...)` is called, before decorating anything. Other inputs have the annotated types; `exceptions` is a tuple of exception classes, possibly empty. Forward all arguments and return the first successful result, including falsey results. Preserve the function's name and docstring with `functools.wraps`.

Only errors matching `exceptions` trigger another attempt (subclasses, more specific kinds of the listed error classes, match too). Before each next attempt, call the injected `sleep(delay_s)` exactly once, even when the delay is zero. Do not sleep before the first attempt, after success, after an unlisted error, or after exhausting attempts. Re-raise the last operation error unchanged when attempts run out. A sleep error propagates immediately. Each invocation gets its own attempt budget.

**Example:** `@retry(3, (OSError,), delay_s=0.2, sleep=record_sleep)` allows up to three operation calls and two calls to `record_sleep(0.2)`.

**Watch out:** Retrying an operation can repeat its effects. Here the caller chooses operations for which repeating the request is acceptable.

**Reread:** contextlib, “Using a context manager as a function decorator”; functools.wraps; Missing Semester, “Debugging” → “Logging” (record attempts and errors).

### E3 — Wait for station readiness with a deadline (medium, ~11 min)

**Goal:** Poll a readiness function without waiting forever between checks.

**Signature:** `with_deadline(fn, timeout_s, clock=time.monotonic, sleep=time.sleep) -> T`

Reject a negative timeout with `ValueError` before calling any dependency. Compute the deadline from the injected clock once, then call `fn()` immediately, even for a zero timeout. Return the exact first truthy result. After a falsey result, raise `TimeoutError` if no time remains. Otherwise sleep for the smaller of 0.01 seconds and the remaining time. Check the clock after sleeping: at or beyond the deadline, raise `TimeoutError` without another `fn()` call. Repeat while time remains. The timeout message is up to you.

The clock returns seconds and never moves backward; sleep advances time. Propagate errors from `fn`, `clock`, or `sleep` immediately. Calls are synchronous (one finishes before the next starts): this helper cannot interrupt a blocked `fn()`. A truthy result from an already-started call is accepted even if that call took past the deadline.

**Example:** if readiness returns `None` then `{"ready": True}`, return that dictionary after one sleep, provided time remains.

**Watch out:** Use the supplied clock and sleep, not calendar time or a real delay hidden inside your code. A zero timeout still permits the immediate check, but never a second one.

**Reread:** contextlib, “Examples and Recipes” → “Catching exceptions from __enter__ methods” (keep the protected operation's exception distinct); Missing Semester, “Debugging” → “Debuggers” (inspect the remaining time).

### E4 — Ramp voltage and recover safely (medium, ~12 min)

**Goal:** Increase a PSU channel from 0 V (volts, the unit of electrical potential) toward a target. A **ramp** is a series of small changes; **settling** is waiting for the instrument to stabilize after a change.

**Signature:** `ramp_voltage(psu, ch, target, step, settle) -> None`

The caller has already set this channel to 0 V and enabled its output. Use `psu.set_voltage(ch, voltage)`; do not read voltage or enable output. Inputs are finite numbers. Reject `target < 0` or `step <= 0` with `ValueError` before any device or settle calls. On valid input, write `min(previous + step, target)` until you reach the target. Call the zero-argument `settle()` after each successful write, including the final one. Never write a value above target. A zero target does nothing; a step larger than target writes target once. Return `None` and leave output enabled on success.

If a voltage write or settle raises any `BaseException`, attempt `set_voltage(ch, 0.0)`, then `output(ch, False)`, then re-raise the original exception object. Attempt both cleanup operations even if either raises; their errors must not replace the original. Do not settle during cleanup. Invalid-input errors need no cleanup because no operation has started.

**Example:** target `5`, step `2` writes `2`, `4`, `5`, with one settle call after each. If settling at `4` fails, the next commands are voltage `0` and output off.

**Watch out:** Use `min` to clamp the last increment. Keep validation outside the recovery block. As in E1, cleanup can only attempt commands when the instrument itself is failing.

**Reread:** Python Tutorial §8.7; contextlib, “Examples and Recipes” → “Replacing any use of try-finally and flag variables”; Missing Semester, “Debugging” → “Logging” (inspect the command sequence).
