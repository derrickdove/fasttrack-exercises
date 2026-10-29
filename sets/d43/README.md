# d43 — Debugging across the hardware–software boundary

**Time:** about 45 minutes · **Read first:** SparkFun, [How to Use a Multimeter](https://learn.sparkfun.com/tutorials/how-to-use-a-multimeter/all), *How to Use an Oscilloscope*, and *How to Read a Datasheet* (apply that reading to the invented excerpt below); *The Pragmatic Programmer*, topic **Debugging** — your book. · **You edit:** `starter/flaky_driver.py` and `starter/notes.md`.

## What you're building

A chassis test station powers connected equipment (the load), reads its supply voltage, and watches a stream of numbered measurements. Operators have reported four failures at the boundary between physical equipment and the software that controls it. Repair each small function using the operator report, the supplied legacy-code excerpt, and the equipment contract; no physical equipment is required.

## How this works

1. Replace the four `raise NotImplementedError(...)` lines in `starter/flaky_driver.py`. Each function's docstring (its embedded description) includes the old, buggy code for diagnosis; those excerpts are deliberately not executable so every exercise starts unfinished. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d43** (or run `bash tools/run.sh d43` / `tools\run.ps1 d43`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Fill the short evidence table in `starter/notes.md` as you go. It is a manual notebook, not an extra graded exercise. Report **all pass / partial / stuck** in the tracker.

A **driver** translates software requests into equipment commands. A **datasheet** states an instrument's supported ranges, accuracy, and interface rules. A **multimeter** measures quantities such as steady voltage; an **oscilloscope** displays voltage over time, using a **trigger** (a condition that starts a capture) to catch a brief event. Neither a passing software test nor a correct display alone proves the physical voltage is correct: compare independent evidence.

A **transport** is the communication layer that sends commands and receives replies. A **callback** is a function passed into another function. Here, callbacks stand in for instrument communication, so tests can supply a **fake**, a small deterministic replacement for hardware. `Callable[[str, float | None], str]` means a callback accepting text and a float-or-None, returning text. A **timeout** limits waiting; a **retry** repeats a failed operation. An **exception** interrupts normal execution; `finally` runs cleanup when execution leaves a `try` block, including by exception. For example, this unrelated operator-log helper always closes its log:

```python
try:
    log.write("step started")
finally:
    log.close()
```

`float` represents a number that can include a fractional part. **Finite** excludes infinity and NaN (a special "not a number" value); `math.isfinite(value)` checks this. `%` is Python's remainder operator: `11 % 8` is `3`.

**V** means volts, **mV** means millivolts (1000 mV = 1 V), and **ms** means milliseconds (1000 ms = 1 second).

## Operator report

| Exercise | What the operator saw | Evidence to start with |
| --- | --- | --- |
| E1 | "Most readings look right, but 500 mV appears as 500 V in the report." | Compare the legacy parser with the response units below. |
| E2 | "If the supply stops answering, the station never returns control." | Compare the legacy query with the timeout convention below. |
| E3 | "A missing-sample alarm disappears when the counter resets to zero." | Captured counters are `[254, 1]`; two samples are missing. |
| E4 | "A measurement exception aborts the step, but the output stays on." | Trace which lines execute after `sample()` raises. |

Reproduce one symptom, make a hypothesis (a possible cause you can check), change the responsible function, and rerun. Record the evidence that supports your repair. Avoid changing unrelated code just because it looks suspicious.

## Bench reference: invented PS-30 supply datasheet (one-page excerpt)

This excerpt is invented for this exercise, not a real product specification.
A **load** is the connected equipment drawing power. **DC** means direct current,
with a steady polarity. **V** means volts, **mV** means millivolts (1000 mV = 1 V),
and **A** means amperes, the unit of current.

| Item | Specification |
| --- | --- |
| Output range | 0.000–30.000 V DC; current limit 0.000–3.000 A |
| Voltage measurement accuracy | ±(0.05% of reading + 2 mV), after settling |
| Settling | Allow 20 ms for the output to stabilize before measuring real hardware |
| Query response | A normal connected supply answers within 200 ms |
| Host timeout | Use 0.25 s by default; the transport accepts a caller-selected finite positive timeout in seconds |
| Missing reply | The transport raises `TimeoutError` when the timeout expires; `None` means wait without a limit |
| Reply format | A decimal number, whitespace, then exactly `V` or `mV`; either unit may appear on any reading; a trailing newline is allowed |

**SCPI** means Standard Commands for Programmable Instruments, a text command
convention. A command ending in `?` is a **query**, which requests a reply.

| Command sent without a newline by this driver | Meaning / response |
| --- | --- |
| `MEAS:VOLT?` | Measure voltage; reply examples: `0.500 V` or `500 mV` |
| `OUTP ON` | Enable the output; no measurement reply |
| `OUTP OFF` | Disable the output; no measurement reply |

Read range, accuracy, and units separately: range says what the supply can do;
accuracy says the allowed measurement error, not the output resolution (the smallest displayed increment). At 5 V,
the accuracy expression gives ±0.0045 V. A 1000-fold discrepancy is far larger.
The command table tells you the exact spelling and response type; the timeout
row describes what happens when there is no reply. Real transports add message
termination and enforce the deadline; this set supplies callbacks instead.
These tests use no sleeps and do not simulate settling or physical measurement accuracy.

## Exercises

### E1 — Repair voltage units (easy, ~10 min)

**Goal:** Return the voltage in volts, regardless of the unit in the reply.

**Signature:** `def voltage_in_volts(reply: str) -> float`

**Contract:** Split on whitespace. Require exactly two fields: a number accepted
by Python's `float()` and the case-sensitive unit `V` or `mV`. Leading/trailing
whitespace, tabs, and newlines are allowed. Convert millivolts to volts; leave
volts unchanged. Raise `ValueError` for the wrong field count, an invalid number,
an unsupported unit, or a nonfinite number. Exception text is not graded.
This parser does not enforce the supply's physical range or round/clamp values;
a finite negative diagnostic reading must still be preserved.

**Example:** `voltage_in_volts("500 mV\n")` → `0.5`.

**Watch out:** Uppercase `MV` is not millivolts. Changing report limits to accept
500 V would hide the defect. In your notebook, say what a multimeter could
confirm independently about the steady output.

**Reread:** SparkFun, *How to Use a Multimeter*, measuring voltage; *How to Read a Datasheet*, units and accuracy; the excerpt's reply-format and command rows.

### E2 — Bound the unanswered query (easy–medium, ~12 min)

**Goal:** Make one voltage query that has a finite waiting limit.

**Signature:** `def query_voltage(exchange: Callable[[str, float | None], str], timeout_s: float = 0.25) -> str`

**Contract:** `exchange(command, timeout_s)` is the supplied transport callback:
it sends the command, waits up to that many seconds for a complete response,
and returns the reply text or raises an exception. Before calling it, require
`timeout_s` to be finite and greater than zero; otherwise raise `ValueError`
without calling it. Call it exactly once, with positional arguments
`"MEAS:VOLT?"` and the validated timeout. Return its text unchanged, including
any newline. Let its exception propagate unchanged; do not retry. You do not
implement the callback's clock, sleep, or transport. The input timeout is a float.

**Example:** If a fake records its arguments and returns `"5 V"`, then
`query_voltage(fake)` returns `"5 V"` and records `("MEAS:VOLT?", 0.25)`.

**Watch out:** Returning `"0 V"` after a timeout invents a measurement. The tests
model silence by raising `TimeoutError` immediately; they reject an unbounded
wait without actually waiting forever. E2 does not call E1.

**Reread:** *The Pragmatic Programmer*, topic **Debugging**, reproducing a failure
and checking assumptions; the datasheet's query-response and host-timeout rows.

### E3 — Repair a gap count at wraparound (medium, ~10 min)

**Goal:** Report how many numbered samples went missing from captured telemetry
(measurements sent from equipment to the station).

**Signature:** `def missing_samples(counters: list[int], modulus: int = 256) -> int`

**Contract:** A **counter** labels each generated sample. The **modulus** is the
number of distinct labels: with 256, the sequence runs 0 through 255 and then
wraps (returns) to 0. Require integer `modulus >= 2` and each integer counter
in `0 <= counter < modulus`; otherwise raise `ValueError`, even for an empty
or one-element list. Inputs are already integers; no type coercion is needed.
For each adjacent pair, the forward distance is `(current - previous) % modulus`.
Identical counters are duplicates and contribute zero missing samples.
Otherwise that pair contributes distance minus one. Sum these contributions;
return 0 for empty or one-element valid input, and leave the input list unchanged.

**Example:** `missing_samples([254, 1, 1, 4])` → `4`: two absent labels between
254 and 1 (255 and 0), none for the duplicate, then two between 1 and 4.

**Watch out:** Assume delivery order is preserved and fewer than `modulus`
new samples separate adjacent captures. Reordered samples or a complete unseen
cycle cannot be distinguished using these counters alone. In your notebook,
explain how an oscilloscope capture might reveal a short supply dip between
software measurements; a gap count alone does not establish its physical cause.

**Reread:** SparkFun, *How to Use an Oscilloscope*, time scale and triggering;
*The Pragmatic Programmer*, topic **Debugging**, isolating the cause using evidence.

### E4 — Turn off the output after a failed step (medium, ~13 min)

**Goal:** Make the supply cleanup run even when the measurement step fails.

**Signature:** `def powered_sample(write: Callable[[str], None], sample: Callable[[], float]) -> float`

**Contract:** Call `write("OUTP ON")`, then `sample()` exactly once, then
`write("OUTP OFF")` exactly once, and return the sample's float unchanged.
Also attempt `OUTP OFF` if enabling the output or taking the sample raises;
an enable failure can mean the command reached the supply but its acknowledgement
(the confirmation sent back) was lost. Do not sample if enabling raises.
After cleanup, propagate the original exception unchanged, including operator
cancellation (`KeyboardInterrupt`). Assume the off command succeeds; handling
failure of the cleanup command is outside this exercise. Neither callback
needs a timeout argument here; the supplied communication layer owns its waits.

**Example:** If sampling raises `TimeoutError`, the write history is still
`["OUTP ON", "OUTP OFF"]`, and that same exception reaches the caller.

**Watch out:** A cleanup line after `sample()` is skipped when sampling raises.
Use `try`/`finally` so cleanup runs on both the normal and exceptional paths.
E4 does not call E1–E3; the supplied sample callback owns measurement details.

**Reread:** *The Pragmatic Programmer*, topic **Debugging**, tracing the failure
and checking assumptions about control flow; SparkFun, *How to Use an Oscilloscope*,
observing the output over time to check the physical effect of a software command.
