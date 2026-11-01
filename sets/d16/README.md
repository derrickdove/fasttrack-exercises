# d16 — Bytes, text and SCPI syntax

**Time:** about 60 minutes · **Read first:** [SCPI in plain words: commands, queries, short forms, error queue (Wikipedia overview)](https://en.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments); [PSU-30 programming guide excerpt](data/psu_programming_guide.md); [Bytes vs text: bytes, encode() and decode()](https://docs.python.org/3/library/stdtypes.html#binary-sequence-types-bytes-bytearray-memoryview); [The Linux Command Line, chapter 10: processes (ps, top, kill)](https://linuxcommand.org/tlcl.php); [Python Tutorial §3.1.2: Text](https://docs.python.org/3/tutorial/introduction.html#text) · **You edit:** `starter/scpi.py`

## What you're building

A chassis test station sends settings to a power supply and asks a meter for measurements. You will build small helpers for SCPI (Standard Commands for Programmable Instruments), a text command language used by instruments. These helpers prepare and read messages locally; no instrument connection is needed.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/scpi.py`. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: d16** (or run `bash tools/run.sh d16` / `tools\run.ps1 d16`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **string** (`str`) holds text; **bytes** hold integer byte values from 0 to 255, as sent over an instrument connection. An **encoding** maps text characters to bytes; **ASCII** is an encoding limited to values 0–127. `encode("ascii")` converts text to bytes; `decode("ascii")` converts bytes to text. A **terminator** is the ending that marks a message boundary, commonly `"\n"` (line feed) or `"\r\n"` (carriage return followed by line feed). **Whitespace** means spaces, tabs, line endings, and other characters removed by `str.strip()`.

```python
label = "station A2"
payload = label.encode("ascii")
assert payload == b"station A2"  # b marks a bytes literal
assert payload.decode("ascii") == label
```

A SCPI **header** is a command's name, such as `MEAS:VOLT?`; colons separate its keyword levels. An **argument** is a supplied value after the header. A **query** requests a reply and has `?` at the end of its header. `*IDN?` is a **common command**, shared across instrument types, that requests identification. An **error queue** stores instrument-reported errors for later queries; E5 reads that queue before enabling power.

A **boolean** (`bool`) is `True` or `False`. For Python, `*args` collects extra positional arguments in a tuple (an ordered collection). `channels=` is a **keyword-only argument**: pass it by name. A **channel** is a numbered instrument input; SCPI writes a channel list as `(@1,2)`. An **exception** signals failure; `ValueError` here means an input cannot be represented under our rules.

The Linux reading explains a **process**, a running program: `ps` lists processes, `top` shows live activity, and `kill` sends a signal (a request such as termination). Those commands help when a station driver hangs; this set requires no process commands.

A **transport** is the connection object that sends instrument text. An **object** groups data and functions; a **method** is a function called through an object, such as `transport.query("*IDN?")`. `write(command)` sends text and returns `None`; `query(command)` sends text and returns its reply as a string. The supplied `Transport` **protocol** is a type declaration listing those required methods. Leave it unchanged; the tests supply a **fake**, an object with scripted replies instead of hardware. `RuntimeError` is an exception used here when the instrument reports an unexpected state.

Use `split(",", 1)` to separate a code from a message at the first comma only; `int()` converts the code text to an integer. A `while True` loop repeats until `break` leaves it or an exception stops the function.

```python
code_text, message = '-100,"Unknown command"'.split(",", 1)
code = int(code_text)
assert code == -100
assert message == '"Unknown command"'
```

## Exercises

### E1 — Prepare a power-supply command (easy, ~9 min)

**Goal:** Turn operator-entered text into bytes the power supply can receive.

**Signature:** `def encode_command(cmd: str, term: str = "\n") -> bytes`

**Contract:** Both `cmd` and `term` must contain only ASCII characters. `term` must not be empty. Raise `ValueError` otherwise. Remove every complete trailing copy of `term` from `cmd`, append one copy, then return ASCII bytes. Leave all other characters, including spaces, unchanged. An empty command is allowed and returns just the terminator. Compare whole terminators, not individual characters.

**Examples:** `encode_command("VOLT 5")` → `b"VOLT 5\n"`; `encode_command("OUTP ON\n\n")` → `b"OUTP ON\n"`; `encode_command("*IDN?", "\r\n")` → `b"*IDN?\r\n"`.

**Watch out:** `UnicodeEncodeError` means encoding encountered a character outside ASCII; catch it and raise `ValueError`. Check for an empty terminator before removing repeated endings.

**Reread:** Bytes vs text, `bytes` and `str.encode()`; SCPI overview, command syntax.

### E2 — Read a meter reply (easy, ~10 min)

**Goal:** Turn a meter's received bytes into text ready for later measurement checking.

**Signature:** `def decode_reply(data: bytes, term: str = "\n") -> str`

**Contract:** Require a nonempty ASCII `term`, or raise `ValueError`. Decode `data` as ASCII; catch `UnicodeDecodeError` and raise a plain `ValueError` instead. First remove at most one exact trailing copy of `term`, if present, then strip surrounding whitespace. Return the resulting string, including `""` for an empty reply. A missing terminator is allowed. Do not convert numbers, change internal spaces, or interpret instrument errors.

**Examples:** `decode_reply(b"  +5.020 \r\n")` → `"+5.020"`; `decode_reply(b"READY||", "|")` → `"READY|"`; `decode_reply(b"  -100, bad command  ")` → `"-100, bad command"`.

**Watch out:** Removal happens before whitespace stripping: `decode_reply(b"READY|  ", "|")` returns `"READY|"`. Stripping may remove additional whitespace terminators, but must not remove additional non-whitespace terminators. A byte such as `b"\xff"` is not ASCII.

**Reread:** Bytes vs text, `bytes.decode()` and the linked `str.strip()` description; Python Tutorial §3.1.2, strings and their methods.

### E3 — Build settings and measurement requests (medium, ~14 min)

**Goal:** Format power-supply settings and requests for selected meter inputs.

**Signature:** `def build(header: str, *args: str | int | float | bool, channels: list[int] | None = None) -> str`

**Contract:** Return `header` unchanged when there are no values or channels. Otherwise append exactly one space, then comma-separated values with no spaces added around commas. Convert booleans to `ON` / `OFF`; convert other arguments with `str()`. Preserve strings literally, including any quotes or spaces they already contain. If `channels` is nonempty, append `(@` plus its comma-separated numbers plus `)` as the final value. `None` and `[]` both omit that value. Preserve channel order and duplicates, and do not modify the input list. Do not add a terminator.

**Examples:** `build("VOLT", 5)` → `"VOLT 5"`; `build("MEAS:VOLT?", channels=[1, 2])` → `"MEAS:VOLT? (@1,2)"`; `build("OUTP", True)` → `"OUTP ON"`; `build("SOUR:VOLT", 2.5, "MIN", channels=[3])` → `"SOUR:VOLT 2.5,MIN,(@3)"`.

**Watch out:** Python treats booleans as a kind of integer, so handle booleans before general conversion. You may assume headers are valid, nonempty ASCII without surrounding whitespace, arguments have the supplied types, floats (decimal numbers) are finite (neither infinity nor NaN, meaning "not a number"), and channel numbers are positive integers. No extra input validation or automatic quoting is required.

**Reread:** SCPI overview, syntax and parameter lists; Python Tutorial §3.1.2, text and string operations.

### E4 — Recognize queries and abbreviate headers (medium, ~12 min)

**Goal:** Help the station identify commands that need replies and display the instrument manual's short names.

**Signatures:** `def is_query(cmd: str) -> bool` and `def short_form(header: str) -> str`

**Contract for `is_query`:** Split the text on whitespace and inspect only the first token (piece). Return `True` exactly when that token ends with `?`. Empty or whitespace-only text returns `False`. Leading/trailing whitespace and arguments are allowed. A `?` in an argument does not make a command a query. Inputs contain at most one command; you do not need to parse multiple commands or validate SCPI grammar.

**Examples:** `is_query("  MEAS:VOLT? (@1,2)\n")` → `True`; `is_query('DISP:TEXT "Ready?"')` → `False`.

**Contract for `short_form`:** A manual's mixed-case notation uses uppercase letters for the required abbreviation and lowercase letters for the optional longer spelling. Remove only lowercase ASCII letters (`a`–`z`), preserving uppercase letters, digits, colons, a leading `*` or `:`, and a trailing `?`. Return a string. Inputs are valid manual-style headers without arguments or whitespace; each keyword already contains its uppercase short form. Do not guess abbreviations for arbitrary lowercase text.

**Examples:** `short_form("MEASure:VOLTage:DC?")` → `"MEAS:VOLT:DC?"`; `short_form(":SENSe1:VOLTage?")` → `":SENS1:VOLT?"`; `short_form("*IDN?")` → `"*IDN?"`.

**Watch out:** Uppercasing the whole header would keep optional letters. `is_query` inspects the header even when channel arguments follow it.

**Reread:** SCPI overview, command/query syntax and uppercase/lowercase short forms; Python Tutorial §3.1.2, string indexing and methods.

### E5 — Follow a programming guide before applying power (medium, ~15 min)

**Goal:** Read [the supplied programming guide excerpt](data/psu_programming_guide.md) and turn its startup procedure into code. Real instrument programming guides are long PDFs; this short original excerpt shows how they read. A **power-up sequence** is the ordered set of checks and settings used before enabling a supply's output.

**Signature:** `def safe_power_up(transport: Transport, volts: float, amps: float) -> list[str]`

**Contract:** Implement only `safe_power_up`; leave the supplied `Transport` declaration unchanged. Use `transport.write(command)` for commands and `transport.query(command)` for queries. Send the exact uppercase spellings below, without terminators. On success return a list of the queries' original reply strings, in call order; do not include commands. The transport handles message endings and a finite timeout (the maximum wait for a reply). Except for the final `OUTP ON` write (step 6), let transport exceptions propagate: stop immediately and send nothing further.

1. Query `*IDN?` first. Apply `.strip()` to a copy of its reply, then split on commas. Require exactly four fields, with the first two exactly `FastTrack` and `PSU-30`. The serial and firmware fields may vary; no further checks on them are required. Otherwise raise `RuntimeError` with text `unexpected identity: <stripped reply>` and make no further calls.
2. Write `*RST`, `*CLS`, and `OUTP OFF`, in that order. Even though this model's reset disables output, send the explicit OFF command before changing limits.
3. Write `CURR ` plus `str(amps)`, then `VOLT ` plus `str(volts)`. The arguments will be finite numbers within the guide's allowed limits; no extra validation or rounding is needed.
4. Query `*OPC?` once. This query waits for earlier operations to finish; no sleep or repeated polling is needed. Require its stripped reply to equal `"1"`. Otherwise raise `RuntimeError` with text `operation did not complete: <stripped reply>` and make no further calls.
5. Drain (read and remove entries from) the error queue using `SYST:ERR?`. Each reply has the guide's valid `code,"message"` format, optionally surrounded by whitespace. Convert the code before the first comma to an integer. Code zero means the queue is empty: stop reading. On the first nonzero code, immediately raise `RuntimeError` whose text is the entire stripped error reply, including its code, quotes, and full message. Do not read another entry or enable output after an error.
6. Only after the empty-queue reply, write `OUTP ON`. Catch `BaseException`, the parent exception type that includes ordinary errors and `KeyboardInterrupt` (raised by Ctrl+C), around this write. If it fails, attempt `OUTP OFF` exactly once, then re-raise (let propagate) the original exception object. This is a **best-effort** attempt: catch `BaseException` around the recovery OFF write too. If OFF also fails, attach a **note** (extra diagnostic text) `cleanup failed: OUTP OFF: <repr of error>; output state unknown` to the original ON failure, then re-raise that original; send nothing else. On success, return the reply list. Keep replies unchanged in that list, even if you stripped copies for checking. Do not send any other commands or queries; `*ESR?` is described in the guide but is not part of this procedure.

`repr(error)` gives the error's Python representation, including its type and message. Python 3.11+ provides `original.add_note(text)` to append a note without replacing the original exception.

**Example:** If the fake returns `"FastTrack,PSU-30,SN0042,1.0"`, `"1"`, and `0,"No error"` for the three queries, `safe_power_up(transport, 5.0, 0.2)` returns `['FastTrack,PSU-30,SN0042,1.0', '1', '0,"No error"']` after enabling the output.

**Watch out:** Setting current before voltage is part of this guide's procedure. A comma inside an error message belongs to that message. Clearing status again after setting limits would hide errors; an instrument-reported error must prevent enabling output. The instrument may have enabled output before the write error came back, so the output state is unknown. Attempting OFF limits that risk, but a failed OFF write leaves the state unknown.

**Reread:** The supplied guide's command table and station startup paragraph.
