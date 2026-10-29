# r3 — Week 3 review: a signal-generator test step

**Time:** about 60 minutes (43 minutes on this week, 17 on earlier weeks) · **Read first:** no new reading; review the d04, d13 and d15–d20 readings named below · **You edit:** `starter/review3.py`

## What you're building

A chassis test station uses a **signal generator**, an instrument that produces a repeating electrical signal, to stimulate an input under test. Build its command driver, turn its output off when a test step ends, and recover instrument replies that arrive in pieces. This set mixes this week with earlier weeks: also load a channel hold list and count commands waiting for replies. Everything runs against supplied fakes or local data; no instrument, network connection, or extra package is needed.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/review3.py`. Don't edit `tests/`. The two `Protocol` declarations are supplied interfaces. Leave them and the supplied `configuration_commands` and `decode_reply` helpers as given.
2. Press Ctrl+Shift+B → **Test: r3** (or run `bash tools/run.sh r3` / `tools\run.ps1 r3`). At first you'll see `Exercises: 0 / 7 passed`. Rerun after each exercise.
3. Report all pass / partial / stuck in the tracker.

Earlier readings to revisit as needed (there is no new reading on review day):

- **d04:** Python Tutorial §7.2, reading files; Python `csv`, `DictReader`; Python `pathlib`, `Path.open`.
- **d13:** *A Common-Sense Guide to DSA*, Big O, stacks and queues; Python `collections.deque`, queue behavior.
- **d15:** Python Tutorial §3, strings versus bytes; Python `bytes` documentation; Wikipedia, “Standard Commands for Programmable Instruments” (overview).
- **d16:** PyVISA, “Communicating with your instrument”; PyVISA-sim documentation.
- **d17:** Python `typing.Protocol` documentation; Python `abc` documentation; *The Pragmatic Programmer*, “Decoupling”.
- **d18:** Python `contextlib` documentation; Python Tutorial §8.7, “Defining Clean-up Actions”; Python `functools.wraps` documentation.
- **d19:** pySerial, “Short introduction” and “URL handlers”; SparkFun, “Serial Communication”.
- **d20:** Python “Socket Programming HOWTO”; Python `socket` documentation, `create_connection` and `settimeout`.

A **driver** translates station actions into instrument commands. A **transport** sends commands and gets replies; a **fake** replaces it with predictable in-memory behavior. **SCPI** (Standard Commands for Programmable Instruments) is the text-command convention used here. A **protocol** describes the methods an object must offer without requiring a particular parent class.

A **callable** is an object you can call, such as a function. **Teardown** is cleanup performed after a test step. An **exception** interrupts normal execution; a bare `raise` inside an exception handler sends the same exception onward. `BaseException` also covers operator interruption with `KeyboardInterrupt`.

**ASCII** encodes basic text as bytes. A **terminator** marks a message boundary: **LF** is the line-feed byte `b"\n"`, and **CR** is the carriage-return byte `b"\r"`. A **frame** is one complete message. Serial links send bytes over a device connection; **TCP** (Transmission Control Protocol) sends an ordered byte stream over a network. Either can deliver part of a frame or several frames together. A buffer holds bytes for later processing.

This unrelated status example joins byte fragments and decodes text:

```python
prefix = b"sta"
chunk = b"tus"
message = (prefix + chunk).decode("ascii")
assert message == "status"
```

## Exercises

### E1 — Script the signal source (easy, ~8 min)

**Goal:** Implement `FakeTransport`, a reusable stand-in for an instrument connection.

**Signatures:**

```python
FakeTransport(replies: dict[str, str])
FakeTransport.write(command: str) -> None
FakeTransport.query(command: str) -> str
```

Copy the supplied reply dictionary at construction so later caller changes do not affect the fake. Start a public `writes: list[str]` as an empty list. `write` appends the command exactly as received. `query` appends its command to the same list, then returns the corresponding scripted reply unchanged; an unknown command raises `KeyError` after being recorded. Queries do not consume replies, so a repeated query returns the same reply. Separate fake instances have separate histories.

**Example:** with `fake = FakeTransport({"*IDN?": "LAB,SG1,42,1.0\n"})`, `fake.query("*IDN?")` returns `"LAB,SG1,42,1.0\n"` and `fake.writes` becomes `["*IDN?"]`.

**Watch out:** Both transport methods use text, with no encoding or terminator added by the fake. Do not invent a reply for an unknown query.

**Reread:** d17 — `typing.Protocol`, protocol examples; *The Pragmatic Programmer*, “Decoupling”.

### E2 — Drive a sine-wave source (easy–medium, ~7 min)

**Goal:** Implement `SignalGenerator` against any object offering the supplied `Transport` methods, rather than depending on `FakeTransport` internals. A **sine wave** is a smoothly repeating waveform. Its **frequency** in hertz (**Hz**) counts repetitions per second; **Vpp** means peak-to-peak volts, the difference between the waveform's highest and lowest voltage.

**Signatures:**

```python
SignalGenerator(transport: Transport)
SignalGenerator.idn() -> str
SignalGenerator.configure(frequency_hz: float, amplitude_vpp: float) -> None
SignalGenerator.output(on: bool) -> None
```

Construction stores the transport and sends nothing. `idn` queries exactly `"*IDN?"` and returns its reply with outer whitespace stripped. `configure` accepts a finite frequency from 1 through 1,000,000 Hz and a finite amplitude from 0 through 5 Vpp, both inclusive. Reject invalid numbers with `ValueError` **before any command is sent**. Finite means neither infinity nor NaN (a special floating-point value meaning “not a number”); `math.isfinite` can check this.

To keep this review short, validation and formatting are supplied: call `configuration_commands(frequency_hz, amplitude_vpp)` once, then write each returned command in order. The helper raises `ValueError` for invalid settings without sending anything. For valid inputs, it returns exactly these three commands: `"FUNC SIN"`, `f"FREQ {frequency_hz:.1f}"`, `f"VOLT {amplitude_vpp:.3f}"`. Validate the original numbers before formatting; do not round them into range. `output(True)` writes `"OUTP ON"`; `output(False)` writes `"OUTP OFF"`. Configuration does not switch the output on. Do not add newline bytes, extra queries, or other commands. Transport exceptions propagate unchanged, with no retries or further configuration commands.

**Example:** `generator.configure(1250.25, 1.25)` writes `["FUNC SIN", "FREQ 1250.2", "VOLT 1.250"]`. Python's fixed-decimal formatting determines rounding.

**Watch out:** An invalid amplitude must not leave a changed frequency behind. Validate both inputs first. Tests also use a transport different from your E1 fake.

**Reread:** d15 — SCPI overview and Python Tutorial §3, strings versus bytes; d16 — PyVISA “Communicating with your instrument”, `query`; d17 — `typing.Protocol` and “Decoupling”.

### E3 — Turn the stimulus off on every exit (medium, ~10 min)

**Goal:** Write a wrapper, a function that surrounds another operation with setup and cleanup, for a measurement step.

**Signature:** `def run_with_output(generator: OutputControl, measure: Callable[[], float]) -> float`

Call `generator.output(True)`, then call `measure()` once, then call `generator.output(False)` and return the measurement unchanged. Attempt output-off exactly once even when enabling the output or measuring raises an exception, including `KeyboardInterrupt`. If enabling fails, do not call `measure`.

If enable or measurement fails, propagate that same exception object after attempting output-off. If cleanup also fails, preserve the original enable/measurement exception. If only output-off fails, propagate that cleanup exception. Never retry, close the transport, or validate the returned measurement. The supplied `OutputControl` protocol allows any instrument with an `output(bool)` method.

**Example:** if `measure()` returns `0.82`, the wrapper returns `0.82`, and the output calls are `[True, False]`. If `measure()` raises `TimeoutError`, the same calls occur and that error reaches the caller.

**Watch out:** A plain `finally` can replace the original error when cleanup itself raises. Keep the original failure as the one reported to the operator.

**Reread:** d18 — Python Tutorial §8.7, “Defining Clean-up Actions”; `contextlib`, cleanup and exception propagation.

### E4 — Separate complete instrument replies (medium, ~8 min)

**Goal:** Recover LF-terminated replies from serial or TCP byte fragments without losing the unfinished reply.

**Signature:** `def split_replies(buffer: bytes, chunk: bytes) -> tuple[list[str], bytes]`

Join `buffer` and `chunk` in that order. Return `(complete_replies, unfinished_tail)`: decode each complete LF-terminated line as ASCII text, dropping its LF and at most one CR immediately before that LF. Keep all other whitespace. Return all complete lines in arrival order, including empty lines. Keep trailing bytes after the last LF unchanged as the tail; do not decode an incomplete line. Empty inputs are allowed. `buffer` is an earlier unfinished tail and therefore contains no LF.

Use the supplied `decode_reply(line)` on each complete line after removing its LF. It removes at most one final CR, decodes ASCII, and translates a decoding failure to `ValueError`; you write the splitting and tail handling. A complete line containing a non-ASCII byte raises `ValueError` instead of `UnicodeDecodeError`. A non-ASCII byte in the unfinished tail is retained until a later call completes that line. This function has no saved state; pass its returned tail as the next call's buffer.

**Example:** `split_replies(b"12", b".5\r\nREADY\npar")` returns `(["12.5", "READY"], b"par")`.

**Watch out:** A CR may arrive in one chunk and its LF in the next. Do not use `strip()`, which would remove meaningful spaces from replies.

**Reread:** d15 — Python `bytes`, splitting and decoding; d19 — pySerial “Short introduction”, line endings; d20 — “Socket Programming HOWTO”, partial receives and message boundaries.

### E5 — Read one reply with a receive budget (medium, ~10 min)

**Goal:** Use E4 in a stateful reader for a station connection. A **receive budget** limits how many receive calls one `read()` may make, so a silent or incomplete response cannot cause an endless loop.

**Signatures:**

```python
ReplyReader(recv: Callable[[int], bytes], max_reads: int = 20)
ReplyReader.read() -> str
```

`recv` is a supplied callable like a socket's `recv`: call it as `recv(1024)`. It returns at most that many bytes; `b""` means the connection closed. The real transport must already have a timeout (a maximum wait for one receive call); this wrapper does not create a socket or measure elapsed time. Here the tests supply immediate fake receives.

Construction must reject `max_reads < 1` with `ValueError` and must not call `recv`. Inputs have the annotated types. Each `read()` returns the next complete reply using E4's decoding rules. Keep any extra complete replies and unfinished bytes for later calls. If a complete reply is already waiting, return it without calling `recv`. Otherwise make at most `max_reads` receive calls for this `read()`; return immediately when a complete reply arrives, even on the last allowed call. The budget resets for every call to `read()`.

Raise `TimeoutError` if that budget is exhausted without a complete reply. Keep the unfinished bytes so a later `read()` can finish them. Raise `ConnectionError` immediately on `b""` before a complete reply. Propagate exceptions from `recv` unchanged without retrying; retain bytes received before that exception. Propagate E4's `ValueError` for a malformed complete line; the reader need not be reusable after malformed input or connection closure. Error-message wording is your choice. Reader instances must not share buffered data.

**Example:** successive receives of `b"1"` and `b".0\n2.0\npar"` let two calls to `read()` return `"1.0"` and `"2.0"`; the second call makes no receive call and the tail `b"par"` remains for the next reply.

**Watch out:** Do not assume one receive call equals one reply. Empty reply text (`""`, from `b"\n"`) is valid and differs from a closed connection (`b""`). This exercise builds on E4.

**Reread:** d20 — “Socket Programming HOWTO”, `recv`, buffering and disconnection; Python `socket`, `settimeout`; d19 — pySerial “Short introduction”, timeout behavior.

### E6 — Load the station's channel hold list (easy, ~8 min)

**Goal:** Load channels that the operator has placed on **hold**, meaning they must be left out of the next hardware run. **CSV** (comma-separated values) is a text table; its first row is a **header** naming the columns. A **set** keeps each distinct channel name once.

**Signature:** `def load_hold_channels(path: str | Path) -> set[str]`

**UTF-8** is a text encoding that supports non-English characters. Open the file as UTF-8 text with `newline=""` and use `csv.DictReader`, which returns each row as a dictionary keyed by header names, so quoted commas inside channel names work. The header is exactly `channel,action`. Every record has a nonempty channel and an action exactly `HOLD` or `RUN`; malformed records are outside this exercise. Return the set of channels appearing in any `HOLD` row. `RUN` rows do not cancel a hold: if any row holds a channel, it stays held. Preserve channel text exactly, including spaces and capitalization. Completely empty lines are ignored. A header-only file returns an empty set. Accept either a string path or a `pathlib.Path` (a filesystem path object). A missing file raises `FileNotFoundError`; do not replace it with an empty set. The file must be closed when the function finishes.

**Example:**

```csv
channel,action
BUS_V,HOLD
TEMP_C,RUN
"J2,pin 4",HOLD
BUS_V,RUN
```

returns `{"BUS_V", "J2,pin 4"}`. Neither channel is measured by this function; it only loads the hold list.

**Watch out:** Splitting text at every comma breaks quoted channel names. Repeated holds appear only once in the returned set.

Reread: d04

### E7 — Size the station's reply backlog (easy–medium, ~9 min)

**Goal:** Find how many instrument commands were waiting for replies at the busiest point in a recorded run. A **backlog** is work still waiting to finish. This models a queue: each reply completes the oldest pending command, though no command identities need to be stored here.

**Signature:** `def peak_backlog(events: list[str]) -> int`

Each event is exactly `"SEND"` or `"REPLY"`; other strings are outside this exercise. Start with no pending commands. A SEND adds one pending command; a REPLY removes one. Return the largest pending count reached at any point. Raise `ValueError` if a REPLY arrives when nothing is pending, even if earlier events were valid. Pending commands at the end are allowed. Empty input returns `0`. Leave the input list unchanged. Do not send commands, wait, or print.

Use **O(n)** time (one pass over the `n` events) and **O(1)** extra storage (only a fixed number of counters). Do not repeatedly rescan earlier events or store one item per pending command. A timed check allows 2 seconds for 400,000 events.

**Example:** `peak_backlog(["SEND", "SEND", "REPLY", "SEND", "REPLY"])` returns `2`, even though only one command remains pending at the end.

**Watch out:** Return the peak, not the final count or total number of sends. Exception-message wording is your choice.

Reread: d13
