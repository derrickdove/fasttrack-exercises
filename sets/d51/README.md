# d51 — Debugging across the hardware–software boundary

**Time:** about 65 minutes · **Read first:** SparkFun, [How to Use a Multimeter](https://learn.sparkfun.com/tutorials/how-to-use-a-multimeter/all), *How to Use an Oscilloscope*, and *How to Read a Datasheet* (apply that reading to the invented excerpt below); *The Pragmatic Programmer*, topic **Debugging** — your book; Python, [time.perf_counter](https://docs.python.org/3/library/time.html#time.perf_counter). · **You edit:** `starter/flaky_driver.py` and `starter/notes.md`.

## What you're building

A chassis test station powers connected equipment (the load), reads its supply voltage, and watches a stream of numbered measurements. Operators have reported four failures at the boundary between physical equipment and the software that controls it. Repair each small function using the operator report, the supplied legacy-code excerpt, and the equipment contract; no physical equipment is required.

## How this works

1. Replace the four `raise NotImplementedError(...)` lines in `starter/flaky_driver.py`. Each function's docstring (its embedded description) includes the old, buggy code for diagnosis; those excerpts are deliberately not executable so every exercise starts unfinished. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d51** (or run `bash tools/run.sh d51` / `tools\run.ps1 d51`). At first you'll see `Exercises: 0 / 6 passed`. Rerun after each exercise.
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

### E5 — Measure the slowest station step (medium, ~12 min)

**Goal:** Summarize how long a test step takes and check its deadline (the latest
allowed completion time). For E5 and E6, edit the new `starter/timing.py` file;
the four earlier repairs and their notebook still work as described above.

**Signature:**

```python
def measure(fn: Callable[[], object], runs: int, clock: Callable[[], float] = time.perf_counter) -> dict[str, float]
def meets_deadline(stats: dict[str, float], deadline_ms: float) -> bool
```

**Contract:** `Callable[[], object]` means a function that takes no arguments and
may return any value. `clock` takes no arguments and returns a time in seconds.
Its readings are finite and never go backwards; subtract two readings to get
elapsed time. The default `time.perf_counter` is Python's high-resolution clock
for elapsed durations (it can distinguish short intervals), including time spent waiting. Its absolute starting
value has no meaning here. Tests pass a fake clock with scripted readings, so
no equipment, sleeps, or real speed measurements are needed.

`runs` is an integer. If it is below 1, raise `ValueError` before calling either
callback. Otherwise, repeat exactly `runs` times: read `clock()`, call `fn()`
once, then read `clock()` again. Ignore the return from `fn`; record
`(end - start) * 1000` in milliseconds. Exclude gaps between runs. If either
callback raises, stop immediately and let the same exception propagate; do not
retry or return partial statistics. Do not round durations.

Return a dictionary with exactly these four string keys and float values:

- `min`: the shortest duration.
- `median`: the middle sorted duration; for an even count, the arithmetic mean
  (sum divided by count) of the two middle durations. `statistics.median` can do this.
- `p99`: the 99th percentile, a duration at or below which at least 99% of the
  measured calls fall. Use the **nearest-rank** rule: sort durations from smallest
  to largest, then select index `ceil(0.99 * n) - 1`, where `n` is their count.
  `math.ceil` rounds up to an integer; list indexes start at zero.
- `max`: the longest duration, the worst case observed in these runs.

With one run, all four values are that duration. Zero durations and repeated
values are valid. For small samples, p99 can equal max.

`meets_deadline` returns `True` exactly when `stats["max"] <= deadline_ms`.
Assume that key exists and both numbers are finite and nonnegative; other
keys are optional and must not affect the decision. Leave `stats` unchanged.
Equality meets the deadline.

**Example:** This fake supplies seconds; each pair brackets one call.

```python
clock_values = iter([0.0, 0.125, 1.0, 1.5, 2.0, 2.25, 3.0, 4.0])
stats = measure(lambda: None, 4, lambda: next(clock_values))
# {"min": 125.0, "median": 375.0, "p99": 1000.0, "max": 1000.0}
meets_deadline(stats, 1000.0)  # True
meets_deadline(stats, 999.0)   # False
```

`iter` creates an iterator that supplies values one at a time; `next` takes its
next value. `lambda: ...` makes a small function with no arguments here.

**Watch out:** A low average can hide one missed deadline. P99 describes the
slow end of typical measurements, but can still exclude the slowest calls;
use max when checking whether every measured call met the limit. Even max is
only an observed worst case, not proof that future calls cannot take longer.
Do not time the whole batch and divide: that loses individual slow calls.

**Reread:** *The Pragmatic Programmer*, topic **Debugging**, reproducing a failure
and checking assumptions; Python, `time.perf_counter`, elapsed-time measurement.

### E6 — Choose where speed work belongs (medium, ~8 min)

**Goal:** Choose a language and an optimization (a change to reduce execution time
or resource use) using timing evidence from the station.

**Signature:** `def speed_answers() -> dict[str, str]`

**Contract:** Return exactly the keys `"Q1"`, `"Q2"`, and `"Q3"`, each mapped to
the uppercase letter of your chosen option (`"A"`, `"B"`, `"C"`, or `"D"`).
One answer per question; do not return the option text.

**Example:** `sorted(speed_answers())` returns `["Q1", "Q2", "Q3"]`.
`sorted` returns the keys in alphabetical order here; choose the answer values yourself.

Use the **Debugging** and `time.perf_counter` readings to reason through the
scenarios below.

**Language choice:** To **profile** code is to measure where its execution time
goes. **Compiled code** is translated into machine instructions before it runs;
C and C++ are commonly used this way.

**Q1.** A new station step has a response-time requirement but no timing measurements
yet. Which approach should guide the choice between Python and C/C++?

- A. Start in C/C++ because equipment-control software always needs compiled code.
- B. Start in Python; measure against the requirement and profile before deciding to change language.
- C. Start in Python and accept it if the average is below the deadline, regardless of slower calls.
- D. Pick whichever language has the shortest source file; code size predicts response time.

<details>
<summary>Why it matters on the job</summary>
Language decisions affect both station maintenance and whether a step meets its requirements.
</details>

**A slow loop:** A **hot loop** is a repeated section that accounts for much of
the runtime. To **vectorize** means to express work on many values as a library
operation instead of a Python loop. A **C-backed library** exposes operations
to Python but executes the underlying computation in compiled C or C++.
This quiz needs no new library installation.

**Q2.** Measurements show that one Python loop processing captured readings misses
the step's deadline. What is the next useful approach?

- A. Rewrite the entire station application in C++ before measuring any smaller change.
- B. Remove the timeout so the loop can always finish successfully.
- C. Profile and measure the loop, then try a C-backed operation or move only that piece to C/C++ and measure again.
- D. Run several copies of the unchanged loop at once; that always makes a single result arrive sooner.

<details>
<summary>Why it matters on the job</summary>
A targeted speed change needs evidence that it solves the delay and preserves the measurement result.
</details>

**Timing evidence:** The **operating system (OS)** manages programs and hardware;
**scheduling** is its choice of which work gets processor time. **Jitter** is
variation in timing between runs. **Target hardware** is the actual station computer
and equipment; **under load** means running its expected competing work too.

**Q3.** A step meets its deadline in repeated runs on a busy Windows laptop. Why
is that insufficient proof of the worst case on the station?

- A. OS scheduling and jitter vary with hardware and competing work; measure on the target station under load.
- B. A busy laptop is automatically more demanding than every station, so it already proves the bound.
- C. `perf_counter` removes scheduling delays, so only the number of Python statements matters.
- D. More laptop repetitions eventually guarantee a worst-case bound for any station computer.

<details>
<summary>Why it matters on the job</summary>
Timing evidence must support the conditions under which the station will actually operate.
</details>

**Watch out:** Passing timing tests on one computer is evidence about those
runs. Keep the requirement, the measured result, and the measurement conditions
clear when explaining a language or optimization decision.

**Reread:** *The Pragmatic Programmer*, topic **Debugging**, checking assumptions
and isolating the cause; Python, `time.perf_counter`; the E6 notes **Language
choice**, **A slow loop**, and **Timing evidence** above.
