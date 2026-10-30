# check34 — Day 34: minimum-ready check

**Time:** about 165 minutes · **Read first:** review day; no new reading. Review the earlier readings named below. · **You edit:** `starter/check34.py`

## What you're building

A chassis test station needs to decide whether its tools are ready, read limits, command a power supply, check measurements, and account for telemetry. These ten new problems test the minimum skills needed to do that work without real hardware. A **test station** is the computer and instruments used to test a chassis; **telemetry** is measurement data sent from a device to that computer.

## How this works

1. Replace the `raise NotImplementedError(...)` bodies in `starter/check34.py`. Don't edit `tests/`. The supplied data classes and `Transport` interface stay as supplied; don't implement the interface's two placeholder methods.
2. Press **Ctrl+Shift+B → Test: check34** (or run `bash tools/run.sh check34` / `tools\run.ps1 check34`). At first you'll see `Exercises: 0 / 10 passed`. Rerun after each exercise.
3. **Time-box this check to 165 minutes:** set a timer, work from E1 to E10, and move on when an exercise's budget expires. The exercises are ordered from easiest to hardest and can be completed independently. Record unfinished exercises and the ones that took longest.
4. Report **all pass / partial / stuck** in the tracker when time is up. Use the reread table to choose your next practice.

The earlier readings to keep nearby are Python Tutorial §5 (data structures), §7.2 (files), and §8 (exceptions); the `csv`, `dataclasses`, `subprocess`, `typing.Protocol`, `collections.deque`, `struct`, and `zlib.crc32` documentation; pytest “Get started” and “How to write and report assertions”; and the day 27 serial-number arithmetic overview. Each exercise identifies the relevant part precisely.

A **test harness** is the supplied test code that calls your work and checks its behavior. An **interface** lists the operations an object promises to provide. A **contract** states inputs, outputs, and errors. A **dataclass** supplies fields, construction, and equality automatically; all four supplied data classes are frozen, meaning you cannot assign new values to their fields. A **callable** is a function or other object that you can call. An **iterable** can supply items one at a time; some iterables can be consumed only once. `None` means no value, and **finite** excludes `nan` (not a number), `inf`, and `-inf`.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Station:
    name: str
bench = Station("chassis-b")
```

The supplied records are `Limit(low: float | None, high: float | None, unit: str)`, `Measurement(name: str, value: float, unit: str)`, `Result(name: str, value: float | None, status: str, message: str)`, and `Packet(seq: int, timestamp_us: int, readings: dict[int, float])`. Construct them directly; their constructors need no learner code. Their fields have the order shown here.

## Exercises

### E1 — Which station tools block readiness? (easy, ~8 min)

**Goal:** Review process results before an operator starts the chassis test. A **process** is a running program; its **exit code** is an integer returned when it finishes. Zero means success; every nonzero value, including a negative signal code, blocks readiness here. A **signal** is a notification to a process, such as a request to stop.

**Signature:** `def blocked_tools(exits: list[tuple[str, int]]) -> list[str]`

Each pair is a tool name and one attempt's exit code. Return the names with **any** nonzero attempt, once each, in Python's normal case-sensitive sorted order. A later success does not erase an earlier failure. Leave the input unchanged. Empty input or only successes returns `[]`. Names are already valid, nonempty strings; do not trim or change case.

**Example:** `blocked_tools([("scope", 0), ("psu", 1), ("psu", 0)])` → `["psu"]`.

**Watch out:** Negative exit codes are failures too.

**Reread:** d03, Python Tutorial §5.4–5.5 (sets and dictionaries); d33, `subprocess` docs, `CompletedProcess.returncode`.

### E2 — Test a low-voltage trip rule (easy+, ~12 min)

**Goal:** Write a pytest test that detects a dangerous boundary mistake. A **trip** means declaring the voltage too low. A **mutant** is a deliberately broken implementation used to check whether your test finds a bug.

**Signature:** `def test_e2_trip_boundary(tripped: Callable[[float, float], bool]) -> None`

The harness supplies `tripped(value, low)`. Its correct contract is `True` exactly when `value < low`; equality must return `False`. Write ordinary pytest `assert` statements exercising values below, equal to, and above a finite low bound. Return `None` implicitly. You may call the supplied function as often as needed with finite numbers. Do not define a replacement implementation or inspect the supplied function's source/name.

Your test must pass for the correct rule and raise `AssertionError` for each of four mutants: `value <= low`, always `False`, always `True`, and `value != low` (incorrectly trips above the bound too). The set's pytest harness calls your test with each function directly; you do not need to create a fixture, import another module, or run a subprocess.

**Example:** A low bound of `2.5` must not trip at `2.5`. Choose your own below/above cases too.

**Watch out:** Merely calling the rule checks nothing. An `assert` checks a condition and raises `AssertionError` when false. Do not catch that error inside your test.

**Reread:** d09, pytest “Get started” (asserting with `assert`) and “How to write and report assertions”.

### E3 — Load a station limit file (medium, ~15 min)

**Goal:** Parse **CSV** (comma-separated values, a text table with one record per line) into limits. A **limit** is the permitted interval for a measurement; a **bound** is either end of that interval. Use `csv.reader` so quoted commas work.

**Signature:** `def load_limits(path: Path) -> dict[str, Limit]`

Read UTF-8 text. Ignore blank physical lines and lines whose first non-whitespace character is `#`. The first remaining line must have exactly the four cells `name,low,high,unit`, in that order. Strip surrounding whitespace from every parsed cell. Each subsequent remaining line has exactly four cells; a quoted cell may contain a comma. Quoted cells do not span physical lines in this format.

Return a dictionary from measurement name to `Limit`. Names and units must be nonempty after trimming; names must be unique and are case-sensitive. Parse nonempty bounds with `float()`. An empty bound means `None`, but at least one bound must exist. Bounds must be finite; if both exist, require `low <= high`. A valid header with no records returns `{}`.

Raise `ValueError` for a bad header, malformed CSV, wrong cell count, duplicate name, empty name/unit, invalid numeric bound, both bounds empty, or reversed bounds. Its message must contain `line N`, with N the **physical, 1-based file line number**, counting comments/blanks. A file with no header raises `ValueError` containing `line 1`. Let file access errors such as `FileNotFoundError` propagate unchanged. No special parsing of comments inside records.

**Example:** A file containing `name,low,high,unit` followed by `rail,4.5,5.5,V` returns `{"rail": Limit(4.5, 5.5, "V")}`.

**Watch out:** Reject `nan` and infinity; equal bounds are valid. Catch parsing errors, not file access errors.

**Reread:** d04, Python Tutorial §7.2 and `csv` docs (`reader`, quoted fields, `strict=True`); d05, Python Tutorial §8.3 (handling exceptions).

### E4 — Configure and read through a fake transport (medium, ~15 min)

**Goal:** Make one power-supply driver operation. A **driver** translates station actions into instrument commands. A **transport** carries commands and replies; the tests supply a fake that records calls. **SCPI** means Standard Commands for Programmable Instruments, the command language used here. A **PSU** is a power supply unit; V means volts.

**Signature:** `def acquire_voltage(transport: Transport, channel: int, volts: float) -> float`

A channel is an independently controlled output. Require integer channel 1, 2, or 3 and finite volts in the inclusive interval 0–30. For invalid input, raise `ValueError` **before any transport call**. Inputs have the annotated types; no need to validate arbitrary Python objects.

For valid input make exactly these calls in order, without adding newline characters:

1. `transport.write(f"INST:NSEL {channel}")`
2. `transport.write(f"VOLT {volts:.3f}")` (exactly three decimal places)
3. `transport.write("OUTP ON")`
4. `transport.query("MEAS:VOLT?")`

Convert the reply with `float()` and return it. Whitespace around a numeric reply is allowed. Invalid text or a non-finite reply raises `ValueError`. Transport exceptions propagate unchanged; stop immediately on failure. Do not close the transport or add further commands. This operation leaves the output enabled; E7 tests the separate teardown policy using independent callbacks (functions supplied by the caller).

**Example:** Channel 2 at 5.25 V writes `INST:NSEL 2`, `VOLT 5.250`, `OUTP ON`, then queries `MEAS:VOLT?`. Reply `"5.125\n"` returns `5.125`.

**Watch out:** A **query** asks for a reply; a write does not. Preserve call order.

**Reread:** d19, `typing.Protocol` docs and The Pragmatic Programmer, “Decoupling”; d16, “Standard Commands for Programmable Instruments” overview; Python Tutorial §7.1.1 (formatted string literals).

### E5 — Check every measurement against its limit (medium+, ~18 min)

**Goal:** Implement a small Themis-style evaluator: compare results with configured limits and report missing or unexpected measurements. **Inclusive** bounds allow equality. Status `PASS` means within limits, `FAIL` means outside them, and `ERROR` means the result cannot be trusted or checked.

**Signature:** `def check_all(measurements: Iterable[Measurement], limits: dict[str, Limit]) -> list[Result]`

Consume measurements once. Return exactly one `Result` per name in the union of measurement names and limit names. First emit all limit names sorted case-sensitively, then all unexpected measurement names sorted. Do not mutate inputs. Empty inputs return `[]`. Limit objects are already valid under E3's rules; names and units in measurements are used exactly as given.

For each name apply the **first matching rule** below. Messages and capitalization are exact:

| Condition | value in Result | status | message |
| --- | --- | --- | --- |
| More than one measurement with this name | `None` | `ERROR` | `duplicate measurement` |
| Limit exists, no measurement | `None` | `ERROR` | `not measured` |
| One measurement, no limit | measured value | `ERROR` | `no limit` |
| Measurement unit differs from limit unit | measured value | `ERROR` | `unit mismatch` |
| Measured value is not finite | measured value | `ERROR` | `non-finite reading` |
| Below a non-None low bound | measured value | `FAIL` | `below low` |
| Above a non-None high bound | measured value | `FAIL` | `above high` |
| Otherwise | measured value | `PASS` | `within limits` |

A `None` bound is unbounded on that side. Matching units is case-sensitive; do not convert units.

**Example:** `check_all([Measurement("rail", 5, "V")], {"rail": Limit(4, 5, "V")})` → `[Result("rail", 5, "PASS", "within limits")]`.

**Watch out:** Duplicate readings are one error result even if they have no limit. A generator (an iterable that supplies items once) must work too.

**Reread:** d02, Python Tutorial §4.1–4.4 (conditions and loops); d03, §5.5 (dictionaries); d06, `dataclasses` docs.

### E6 — A bounded voltage alarm window (medium+, ~18 min)

**Goal:** Keep the latest readings in a **deque**, a queue supporting efficient removal at the front and insertion at the back. A **window** is the most recent fixed number of readings; its mean is their sum divided by their count.

**Signatures:** `WindowAlarm(size: int, threshold: float)` and `add(value: float) -> bool | None`.

In `__init__`, require `size > 0` and a finite threshold, else raise `ValueError`. Size is an integer. Each instance owns an initially empty public `values: deque[float]` with `maxlen == size`, its `size`, and its `threshold`. Callers only inspect these fields; they will not edit them.

`add` rejects non-finite values with `ValueError` **without changing state**. Otherwise retain this reading and the previous `size - 1` readings, oldest first. Return `None` until there are `size` readings. Once full, return a bool indicating whether the mean is **strictly greater** than threshold; equality returns `False`. Size 1 works immediately. Instances must not share state.

Keep a running sum and subtract the oldest reading before a full deque discards it. Each update must take constant work regardless of size: **O(1)** means the amount of work does not grow with window size. Do not recompute `sum(values)` every time. The speed check runs 200,000 updates with size 20,000 in at most 2 seconds; use normal station-scale numbers, not extreme floating-point magnitudes.

**Example:** For size 2, threshold 3, adding `[2, 4, 6]` returns `[None, False, True]` and leaves `values` equal to `deque([4, 6], maxlen=2)`.

**Watch out:** A bounded deque automatically drops the oldest item when full; account for its value before appending.

**Reread:** d15, `collections.deque` docs (`maxlen`, `append`), and A Common-Sense Guide to DSA, chapters on Big O and queues.

### E7 — Teardown without hiding the real failure (hard, ~18 min)

**Goal:** Ensure **teardown** (cleanup that makes the station safe after work) tries to turn off the output even if setup or measurement fails. A callback is a callable supplied to another function.

**Signature:** `def guarded_read(enable: Callable[[], None], measure: Callable[[], float], disable: Callable[[], None]) -> float`

Call `enable()` once, then `measure()` once if enable succeeded. Always attempt `disable()` exactly once, including if enable partially changed the hardware and then raised. On complete success return the measurement unchanged. There is no validation or retry in this wrapper.

If enable or measure raises **any `BaseException`**, including `KeyboardInterrupt` from an operator stopping the test, attempt disable and re-raise the original exception object. A disable failure must not replace that original exception. If enable and measure both succeed but disable raises, propagate the disable exception unchanged. Stop calling later work after a failure; never run measure after an enable failure. The callbacks do not take arguments.

**Example:** If measure raises `TimeoutError("no reading")`, the order is enable, measure, disable; the caller receives that same timeout even if disable also fails.

**Watch out:** `Exception` does not include `KeyboardInterrupt`. A bare cleanup exception can accidentally hide the useful failure.

**Reread:** d20, Python Tutorial §8.7 (“Defining Clean-up Actions”) and `contextlib` docs (cleanup on exceptional exits); d05, §8.4 (raising exceptions).

### E8 — Parse and validate a telemetry packet (hard+, ~23 min)

**Goal:** Decode the same binary packet layout used in the capstone. A **packet** is one complete message of bytes. A **CRC** (cyclic redundancy check) is a computed integer used to detect corrupted bytes. **Big-endian** stores the most significant byte first. `u16`, `u64`, `u8`, and `u32` mean unsigned integers of 16, 64, 8, and 32 bits; `f32` is a 32-bit floating-point value.

**Signature:** `def parse_packet(data: bytes) -> Packet`

The byte layout is:

| Field | Format | Meaning |
| --- | --- | --- |
| sync | u16 | Exactly hexadecimal `0xEB90`, marks the packet start |
| seq | u16 | Sequence number, 0–65535 |
| timestamp_us | u64 | Timestamp in microseconds (one millionth of a second) |
| count | u8 | Number of readings, 0–255 |
| repeated count times | u8 then f32 | Channel identifier then its value |
| crc | u32 | `zlib.crc32` of all preceding bytes, excluding the CRC itself |

Use `struct` with the `>` prefix for big-endian: the header is `>HHQB` (13 bytes), each reading `>Bf` (5 bytes), and CRC `>I` (4 bytes). Total length must be exactly `17 + 5 * count`; this function accepts one packet, with no trailing bytes. Return `Packet(seq, timestamp_us, readings)` where readings maps channel integers to decoded floats. Channels may arrive in any order; all 0–255 channel identifiers are valid. Empty readings are valid. Accept all decoded f32 values, including non-finite ones; later result checking decides whether a measurement is usable.

Raise `ValueError` for fewer than 17 bytes, wrong sync, length disagreement, CRC mismatch, or duplicate channel identifiers (even with a valid CRC). Other error text is your choice. Validate lengths before unpacking so malformed bytes do not leak `struct.error`. Do not alter the input. Float32 decoding may round values; compare them with `pytest.approx` in your own experiments.

**Example:** A valid packet with seq 42, timestamp 1000, and one channel/value pair `(7, 1.5)` returns `Packet(42, 1000, {7: 1.5})`. No packet builder is required.

**Watch out:** CRC covers the header too. A repeated channel must not silently overwrite the first value in a dictionary.

**Reread:** d26, `struct` docs (byte order, format characters, `unpack_from`), `zlib.crc32` docs, and the “Endianness” overview.

### E9 — Track missing telemetry across wraparound (hardest, ~23 min)

**Goal:** Implement a **gap tracker**, which remembers missing sequence numbers and recovers them when late packets arrive. A **sequence number** labels a packet in transmission order. **Wraparound** means 65535 is followed by 0. A **duplicate** repeats a recently received sequence; **out of order** means an unseen packet arrives behind the current forward position.

**Signatures:** `GapTracker()` and `update(seq: int) -> list[int]`.

Initialize public counters `received`, `duplicates`, and `out_of_order` to 0, and `missing: set[int]` to an empty set. Each instance has independent state. Inputs are integers; outside 0–65535 raise `ValueError` without changing anything.

For every valid update increment received, even for duplicates. Keep the sequence numbers from the **previous 1024 valid update calls**, including repeated numbers. Check for membership in that window **before** appending this arrival and evicting its oldest entry. If it is a duplicate, increment duplicates and return `[]`; do not increment out_of_order or change the forward anchor. A sequence ceases to be a duplicate when all its occurrences have left that window.

For a nonduplicate, remove seq from missing if present. On the first arrival, set the forward anchor to seq and return `[]`. Otherwise compute signed serial distance from the anchor:

`difference = (seq - anchor + 32768) % 65536 - 32768`

- If difference is positive, return the numbers strictly between anchor and seq in forward order, wrapping modulo 65536. Add those numbers to missing, then move anchor to seq. Adjacent numbers produce `[]`.
- If difference is zero or negative, increment out_of_order and return `[]`. Leave anchor unchanged. Exactly half the sequence range (difference `-32768`) is defined as behind for this exercise.

`missing` holds sequence labels still missing, rather than historical packet counts. Return a new list so changing a returned list cannot change the tracker's state. Public counters and missing are inspected by callers, who will not edit them. You need not parse bytes or run a socket receiver.

**Example:** Updates `[65534, 1, 0, 1, 2]` return `[[], [65535, 0], [], [], []]`. Final counters are received 5, duplicates 1, out_of_order 1, and missing `{65535}`.

**Watch out:** A late arrival can fill a gap but must not move the anchor backward. Duplicate detection takes precedence over the serial-distance calculation.

**Reread:** d27, “Serial number arithmetic” overview and `collections.deque` docs; RFC 1982 §3 is optional background. This contract explicitly resolves the half-range case and defines what enters the duplicate window.

### E10 — Throttle repeated alarms (medium+, ~15 min)

**Goal:** Keep the station's alarm display from flooding the operator. A **throttle** limits how often an action is allowed. Decide whether to display each incoming alarm using only the alarms already allowed in a moving time window.

**Signatures:** `AlarmThrottle(clock: Callable[[], int], window_ms: int, max_alarms: int)`, `allow() -> bool`, and `__len__() -> int` (called by `len(throttle)`).

The supplied `clock` is a callable returning integer milliseconds and never going backwards. Pass this function into the constructor and call it to get the current time; the tests use a fake clock so no real waiting is needed. A millisecond is one thousandth of a second. Each instance starts with its own empty alarm history.

Require `window_ms` and `max_alarms` to be positive integers, else raise `ValueError`. Reject booleans as well as floats, strings, and other non-integers: Python treats `bool` as a kind of `int`, but `True` is not a valid setting here. Do not validate the supplied clock's return values.

On each `allow()` call, read `now` from the clock and remove expired allowed alarms. An earlier allowed alarm at time `t` counts **exactly while `now - t < window_ms`**; it expires when `now - t == window_ms`. If fewer than `max_alarms` allowed alarms remain, record `now` and return `True`. Otherwise return `False` and record nothing. Multiple allowed alarms in the same millisecond each occupy a slot. A rejected alarm must not extend the wait for the next allowed alarm.

Use a deque of allowed alarm times, oldest first, and remove expired times from its left. Store at most `max_alarms` times, including during a long burst of rejected alarms. `len(throttle)` returns the number of stored times without reading the clock or expiring anything; expiry happens in `allow()`. Callers only inspect this length. Each stored time should be appended and removed once, rather than scanning the whole history on every call. The speed check makes 200,000 `allow()` calls in under 2 seconds.

**Example:** With `window_ms=100` and `max_alarms=2`, calls at clock times `[0, 40, 99, 100, 140]` return `[True, True, False, True, True]` and leave `len(throttle) == 2`. At 100 ms the alarm from 0 ms has expired; the rejected alarm at 99 ms used no slot.

**Watch out:** This window counts allowed alarms, not attempts. Expire all old entries before checking capacity, including after a long idle gap.

**Reread:** d27, events-in-the-last-N-ms counter (deque over time, injected clock); d15, `collections.deque` docs (`append`, `popleft`).

## If you failed Ek, reread dXX

| Failed exercise | Reread days and focus |
| --- | --- |
| E1 | d03 sets/sorting; d33 exit codes in `subprocess` |
| E2 | d09 pytest assertions and boundary cases |
| E3 | d04 CSV/files; d05 exceptions and useful error messages |
| E4 | d16 SCPI commands; d19 fake transports and validation before writes |
| E5 | d02 comparisons; d03 grouping by name; d06 dataclasses |
| E6 | d15 bounded deques, running sums, and constant work per update |
| E7 | d05 exception propagation; d20 cleanup even when setup fails |
| E8 | d26 binary formats, byte order, lengths, and CRC |
| E9 | d27 gaps, duplicate windows, wraparound, and late recovery |
| E10 | d27 events-in-the-last-N-ms counter (deque over time, injected clock); d15 deques |
