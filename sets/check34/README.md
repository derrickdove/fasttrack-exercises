# check34 — Day 34: minimum-ready check

**Time:** about 165 minutes · **Read first:** review day; no new reading. Review the earlier readings named below. · **You edit:** `starter/check34.py`

## What you're building

A chassis test station needs to launch its tools, read limits, command a power supply, check measurements, exchange instrument replies, and stop a telemetry listener cleanly. These ten new problems test the minimum skills needed to do that work without real hardware. A **test station** is the computer and instruments used to test a chassis; **telemetry** is measurement data sent from a device to that computer. A **listener** is code that waits for incoming traffic.

## How this works

1. Replace the `raise NotImplementedError(...)` bodies in `starter/check34.py`. Don't edit `tests/`. The supplied data classes and `Transport` interface stay as supplied; don't implement the interface's two placeholder methods. In E10, complete only the two marked learner methods; keep its supplied code.
2. Press **Ctrl+Shift+B → Test: check34** (or run `bash tools/run.sh check34` / `tools\run.ps1 check34`). At first you'll see `Exercises: 0 / 10 passed`. Rerun after each exercise.
3. **Time-box this check to 165 minutes:** set a timer, work from E1 to E10, and move on when an exercise's budget expires. The exercises can be completed independently. E10 includes 10 minutes of code work plus 5 minutes reserved for reading these instructions and rerunning tests throughout the check. Record unfinished exercises and the ones that took longest.
4. Report **all pass / partial / stuck** in the tracker when time is up. Use the reread table to choose your next practice.

The earlier readings to keep nearby are Python Tutorial §5 (data structures), §7.2 (files), and §8 (exceptions); the `csv`, `dataclasses`, `subprocess`, `socket`, `threading`, `queue`, `typing.Protocol`, `collections.deque`, `struct`, and `zlib.crc32` documentation; pytest “Get started” and “How to write and report assertions”; and the day 27 serial-number arithmetic overview. Each exercise identifies the relevant part precisely.

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

### E1 — Launch a station tool (easy, ~8 min)

**Goal:** Run a tool before an operator starts the chassis test. A **process** is a running program; a **subprocess** is a program launched by your Python program. Its **exit code** is the integer it returns when it finishes: zero means success, and nonzero means failure. **Standard output** (`stdout`) is its normal text output; **standard error** (`stderr`) is its separate diagnostic output.

**Signature:** `def run_tool(args: list[str], timeout: float) -> tuple[int, str, str]`

Launch `args` once with `subprocess.run`: the first item names the program, and later items are its arguments (input strings). Capture stdout and stderr separately as **UTF-8** text (a character encoding: rules for storing text). Return `(exit_code, stdout, stderr)` without trimming whitespace. A nonzero exit code is a result to return, not an exception. Do not change `args`.

The list is nonempty and already valid; `timeout` is a finite positive number of seconds. A **timeout** limits how long an operation may wait. Pass it to `subprocess.run`. If it expires, the child process (the launched program) must be killed and waited for before `subprocess.TimeoutExpired` propagates unchanged. A missing executable raises `FileNotFoundError` unchanged. `subprocess.run` already handles timeout cleanup for you. Do not launch a shell (a command interpreter); pass the argument list directly, so spaces and punctuation remain literal argument characters. Use `capture_output=True`, `text=True`, `encoding="utf-8"`, and `check=False`.

**Example:** After `import sys`, `run_tool([sys.executable, "-c", "print('ready')"], 5.0)` → `(0, "ready\n", "")`. `sys.executable` is the path to the Python interpreter currently running; `-c` asks it to execute the following Python source string. This works on Windows and Linux without an external tool installation.

**Watch out:** Return both output streams even when the exit code is nonzero. Do not catch a timeout and pretend the tool succeeded.

**Reread:** d33, `subprocess` docs (`run`, `CompletedProcess`, `TimeoutExpired`), and `sys.executable`.

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

### E6 — Read fragmented instrument replies (medium+, ~18 min)

**Goal:** Exchange one instrument request over **TCP** (Transmission Control Protocol), a connection that delivers bytes in order. A **byte** is a number from 0 to 255; Python's `bytes` stores a sequence of bytes, written as `b"..."`. A **socket** is a Python object that sends and receives network bytes. TCP is a byte stream: a reply can be **fragmented** (split across receives), and replies can be **coalesced** (combined in one receive). A receive boundary is not a message boundary.

**Signature:** `def exchange_lines(connection: socket.socket, command: str, reply_count: int) -> list[str]`

The harness supplies an already connected TCP socket with a positive timeout. Its fake server is **loopback-only**: address `127.0.0.1` connects to this same computer, with no network hardware or internet. The operating system chooses an unused **port** (a numbered endpoint) when the server binds to port `0`. You do not create or connect a socket in this exercise.

Send `command` encoded as **ASCII** (the character encoding used by these instrument commands), followed by exactly one newline byte `b"\n"`, using `connection.sendall`. `sendall` sends all the supplied bytes or raises an error. The command is valid ASCII and contains no newline; `reply_count` is a positive integer. No input validation is needed.

Use `connection.recv(4096)` to receive up to 4096 bytes at a time. Accumulate bytes until you have exactly `reply_count` complete lines. Each line ends with `b"\n"`. Decode each line as ASCII and return the strings in arrival order, removing only the terminating newline. Preserve spaces and empty lines. Keep unfinished bytes between receives, and extract all complete lines already received before receiving again. The server sends exactly the requested number of ASCII lines; this function is used for one exchange per connection.

An empty receive `b""` means **EOF** (end of the stream: the server at the other end closed the connection). If EOF arrives before all requested newline-terminated lines, raise `ConnectionError`, including when an unfinished line remains. Let `TimeoutError` and other socket errors propagate unchanged. The socket's timeout bounds each send/receive separately; leave that setting unchanged. The caller owns and closes the socket, on success or error. Do not close it here, retry, or use sleeps.

**Example:** For command `"MEAS:VOLT?"`, count `2`, and server sends `b"5."` followed by `b"125\nOK\n"`, return `["5.125", "OK"]`. The request bytes are `b"MEAS:VOLT?\n"`. TCP may regroup those server sends; the result must stay the same.

**Watch out:** `recv` may return fewer bytes than requested. Do not discard the bytes after the first newline or treat partial text as a complete reply.

**Reread:** d23, TCP stream framing (using newline bytes to mark message ends); `socket` docs (`sendall`, `recv`, timeouts).

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

### E10 — Receive telemetry and stop cleanly (medium+, ~15 min: 10 code + 5 slack)

**Goal:** Finish a supplied **UDP** (User Datagram Protocol) listener. UDP delivers separate messages called **datagrams**; a receive returns one datagram rather than part of a TCP stream. A **listener** waits for incoming traffic. A **thread** runs work alongside the main program; a **worker** is the thread doing the receive work.

**Signatures:** `UdpListener()`, `receive_once() -> bytes | None`, and `stop() -> None`.

Keep the supplied constructor and `_run` loop. They bind (assign an address to) a UDP socket at `127.0.0.1` and port `0`, set a 0.05-second receive timeout, and start one worker. `listener.address` is the assigned `(host, port)` pair. `listener.packets` is a `queue.Queue[bytes]`, a container that safely transfers items between threads. The worker stores one item per datagram. Read one with `listener.packets.get(timeout=2.0)`; this bounds the wait to two seconds. Instances own separate sockets, queues, and threads.

Complete only the methods marked `LEARNER`:

- `receive_once`: call `self._socket.recvfrom(65535)`, which returns `(data, sender_address)` for one datagram of at most 65535 bytes. Return `data` unchanged, including `b""` for an empty datagram. On `TimeoutError` (also named `socket.timeout`) return `None`, so the worker can check whether to stop. Let other errors propagate. Do not change the socket timeout or close it here.
- `stop`: call `self._stopping.set()` to request that the worker finish, then `self._thread.join(timeout=1.0)`. An **Event** is a thread-safe flag: `set()` raises it, and `is_set()` checks it. A **join** waits for a thread to finish; a join timeout does not itself stop the thread. If `self._thread.is_alive()` after the join, raise `TimeoutError`. Otherwise, if `self.error` is not `None`, raise that same saved exception object. On normal completion return `None`. Calling stop repeatedly is safe; each call still reports a saved worker error.

The supplied worker checks the stop flag between receives, records any failure in `self.error`, and always closes its socket before it finishes. Its `idle` Event is set after the first receive timeout; tests use it to confirm a quiet instrument does not stop the listener. Let the receive timeout wake the worker so it can see the stop flag; keep socket cleanup in the supplied worker. Do not add sleeps or create extra threads. Always call `stop()` when finished, including after an error in the caller.

**Example:** After creating `listener = UdpListener()`, sending the datagram `b"rail=5.0"` to `listener.address` makes `listener.packets.get(timeout=2.0)` return `b"rail=5.0"`. After `listener.stop()`, the worker is finished and its socket is closed.

**Watch out:** An empty UDP datagram is valid data, unlike TCP EOF. A receive timeout means no datagram arrived yet; it must not terminate the worker.

**Reread:** d25 UDP datagrams; d31 `threading.Event`, `Thread.join`, and `queue.Queue`; `socket.recvfrom` docs.

**Budget:** Spend about 10 minutes on these two methods. Reserve the other 5 minutes in this slot for reading the check's instructions and rerunning tests across the set.

## If you failed Ek, reread dXX

| Failed exercise | Reread days and focus |
| --- | --- |
| E1 | d33 subprocess arguments, output capture, exit codes, and timeout cleanup |
| E2 | d09 pytest assertions and boundary cases |
| E3 | d04 CSV/files; d05 exceptions and useful error messages |
| E4 | d16 SCPI commands; d19 fake transports and validation before writes |
| E5 | d02 comparisons; d03 grouping by name; d06 dataclasses |
| E6 | d23 TCP byte streams, newline framing, partial receives, and timeouts |
| E7 | d05 exception propagation; d20 cleanup even when setup fails |
| E8 | d26 binary formats, byte order, lengths, and CRC |
| E9 | d27 gaps, duplicate windows, wraparound, and late recovery |
| E10 | d25 UDP datagrams; d31 stop Events, bounded joins, and queues |
