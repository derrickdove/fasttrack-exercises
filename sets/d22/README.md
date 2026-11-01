# d22 — Serial devices with pyserial

**Time:** about 60 minutes · **Read first:** [SparkFun: Serial Communication](https://learn.sparkfun.com/tutorials/serial-communication/all) (baud, framing, UART); [SparkFun: Serial Peripheral Interface (SPI)](https://learn.sparkfun.com/tutorials/serial-peripheral-interface-spi/all); [SparkFun: I2C](https://learn.sparkfun.com/tutorials/i2c/all); [pySerial: Short introduction](https://pyserial.readthedocs.io/en/latest/shortintro.html) and [URL handlers: loop://](https://pyserial.readthedocs.io/en/latest/urlhandler.html#loop); [Linux device management: udev overview](https://en.wikipedia.org/wiki/Udev) · **You edit:** `starter/serial_sensor.py`

## What you're building

A chassis test station reads temperature and pressure from a serial sensor. You will open a simulated connection, exchange complete lines, check each measurement's checksum, and count damaged messages without losing good readings. Everything runs without hardware on Windows or Linux.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/serial_sensor.py`. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: d22** (or run `bash tools/run.sh d22` / `tools\run.ps1 d22`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **serial connection** carries bits one after another. A **UART** (universal asynchronous receiver/transmitter) converts bytes to serial signals; **baud** measures signal changes per second. **8N1** means eight data bits, no parity bit (an extra error-checking bit), and one stop bit. pySerial defaults to 9600 baud and 8N1; keep those defaults here.

A **bus** is a set of wires and communication rules connecting devices. **SPI** (Serial Peripheral Interface) and **I2C** (Inter-Integrated Circuit) are other serial interfaces to compare with UART. A **clock line** carries a repeating timing signal. A **chip-select** line selects a chip electrically; an **address** is a number in a message that identifies a device. **Full-duplex** means sending and receiving at the same time; **half-duplex** means taking turns. For E5, count only signal wires, excluding power and **ground** (the shared voltage reference). Use the linked SPI and I2C readings to decide which properties belong to each interface.

A **port** is the connection object. A **timeout** bounds how long a read or write waits, in seconds. A **URL handler** selects a connection from a string: `loop://` is a software **loopback**, which returns bytes written to it. It needs no physical device. On Linux a USB serial adapter often appears as `/dev/ttyUSB0`; the `dialout` group commonly grants access, and **udev** manages device nodes (files representing devices), permissions, and stable names. You do not change Linux settings in this set.

**ASCII** encodes basic text as bytes. **Framing** marks message boundaries: **CRLF**, `\r\n`, is carriage return (**CR**) followed by line feed (**LF**). `port.write(...)` takes bytes; `port.readline(size)` returns bytes through the next `\n`, or partial/empty bytes when its timeout expires. The `size` argument limits the number of bytes returned by one call, including the line ending. `encode("ascii")` converts text to bytes; `decode("ascii")` reverses it. A **buffer** holds bytes waiting to be read.

A **frame** is one sensor message. A **checksum** is a small value calculated from message content to detect damage. **XOR**, Python's `^`, combines bits; applying it to each character's ASCII code produces our checksum. **Hexadecimal** (base 16) writes a byte using two digits from `0–9` and `A–F`. This is the NMEA-style checksum used by marine navigation messages, applied to our sensor format. A **dictionary** maps labels to values; a **tuple** groups return values, such as `(frames, bad)`.

```python
code = ord("A")          # ASCII code: 65
combined = code ^ ord("B")
print(f"{combined:02X}")  # 03: two hexadecimal digits
raw = "READY\r\n".encode("ascii")
print(raw[:-2].decode("ascii"))  # READY
```

## Exercises

### E1 — Open a station loopback (easy, ~7 min)

**Goal:** Open an already usable connection with `serial.serial_for_url("loop://", ...)`. Return it with both `timeout` and `write_timeout` set to the supplied seconds. Keep pySerial's other defaults. The caller owns closing the port; a `with` statement closes it automatically.

**Signature:** `def open_loopback(timeout: float) -> serial.Serial`

**Example:** `with open_loopback(0.05) as port:` gives an open loopback with a 0.05-second read timeout and write timeout.

**Watch out:** Inputs are finite floats. Zero is allowed (return immediately); a negative timeout raises `ValueError`, as pySerial already does. Tests use real loopback connections, never physical serial devices. The annotation names pySerial's serial-port interface; the URL handler supplies its implementation.

**Reread:** pySerial Short introduction, “Opening serial ports” and “Testing ports”; URL handlers, “loop://”; SparkFun, “Baud Rate” and “Framing the data”; udev overview for real Linux devices.

### E2 — Exchange complete command lines (easy, ~11 min)

**Goal:** Send an operator command and receive one complete reply.

**Signatures:** `def send_line(port: serial.Serial, text: str) -> None` and `def read_line(port: serial.Serial) -> str`

- `send_line` encodes ASCII text and appends exactly one `\r\n`. Empty text is allowed. Reject embedded `\r`, embedded `\n`, or non-ASCII text with `ValueError`, before writing any bytes. Return `None`.
- `read_line` calls `port.readline(MAX_LINE_BYTES)` once, using the supplied `MAX_LINE_BYTES = 256`, a **module constant** (a fixed named value defined outside the functions). A **chunk** is the bytes returned by that one call. If it returns `b""`, raise `TimeoutError`. If the chunk does not end in `b"\r\n"`, including when cut off at the byte limit, raise `ValueError` for missing CRLF. Otherwise remove exactly those final two bytes and decode ASCII; non-ASCII bytes raise `ValueError` (Python's `UnicodeDecodeError` is a subclass of it). Preserve spaces and other payload characters. A complete line of exactly 256 bytes, including CRLF, is valid.

**Example:** `send_line(port, "STATUS?")` writes `b"STATUS?\r\n"`; on loopback, the next `read_line(port)` returns `"STATUS?"`. A received `b"\r\n"` returns `""`, which is a valid blank line, different from silence.

**Watch out:** A partial reply consumed before timeout is damaged and raises `ValueError`; do not save it for the next call. A bare `\n` ending is also damaged. Calls leave the port open and do not discard unread replies. Assume these short writes complete or pySerial raises an error; let connection/write errors propagate (reach the caller).

**Reread:** pySerial Short introduction, “Readline” and “Opening serial ports” (bytes and timeout examples); SparkFun, “Framing the data”.

### E3 — Validate sensor measurements (medium, ~17 min)

**Goal:** Parse one line after E2 removed CRLF. Require ASCII text in the exact form `$payload*HH`, with one `*` and exactly two hexadecimal checksum digits (upper or lower case). XOR the ASCII codes of every character between `$` and `*`, including commas. Start the checksum at zero; exclude `$`, `*`, and `HH`. A mismatch raises `ValueError`.

**Signature:** `def parse_sensor_line(line: str) -> dict[str, float]`

The payload is one or more comma-separated label/value pairs, such as `TMP,23.5,PRS,101.2`. Labels must be nonempty and are case-sensitive. Convert values with `float`; return a dictionary. Repeated labels keep the last value, matching ordinary dictionary assignment. Missing markers, invalid checksum digits, incomplete pairs, empty labels, and values rejected by `float` also raise `ValueError`. Do not strip the whole line or accept a trailing CRLF here.

**Example:** `parse_sensor_line("$TMP,23.5,PRS,101.2*02")` → `{"TMP": 23.5, "PRS": 101.2}`.

**Watch out:** Include every comma in the checksum. For the example above, `*4F` is a mismatch and must be rejected. No measurement units or physical pass/fail limits are evaluated here.

**Reread:** SparkFun, “Parity bits” (error detection); pySerial Short introduction, “Readline” (receiving bytes). The checksum rule and Python example above define this station's message format completely.

### E4 — Collect good station frames (medium, ~18 min)

**Goal:** Reuse E2 and E3 to collect `count` valid measurement dictionaries, in arrival order. Skip any line for which either helper raises `ValueError`, and add one to `bad` for that line. Return `(frames, bad)` when you have exactly `count` good frames. Corrupted lines do not use up the requested good-frame count.

**Signature:** `def read_frames(port: serial.Serial, count: int, *, max_bad: int = 20) -> tuple[list[dict[str, float]], int]`

A **bad-frame budget** limits the total rejected lines in one call. `max_bad` is a **keyword-only argument**: the `*` means you must name it, as in `read_frames(port, 1, max_bad=3)`. It defaults to 20. When `bad` reaches `max_bad`, immediately raise `ValueError` with a message mentioning the bad-frame budget and its limit; do not read another line or return partial results. Good frames do not reset `bad`. Together with E2's byte limit, this stops a continuously corrupt sensor even when reads never time out or the sensor never sends LF.

**Example:** Given a bad-checksum line, then `$TMP,23.5,PRS,101.2*02`, requesting one frame returns `([{"TMP": 23.5, "PRS": 101.2}], 1)`. With `max_bad=1`, the same input raises `ValueError` on the first line and leaves the good line unread.

**Watch out:** `count` and `max_bad` are integers. Validate both before reading: a negative `count` or a zero or negative `max_bad` raises `ValueError`, even if `count` is zero. With a valid budget, zero `count` returns `([], 0)` without reading. Stop immediately after enough good frames so later bytes remain unread. Let `TimeoutError` and connection errors propagate; do not retry silence forever or return partial results on timeout. Keep the port open. A bad complete line is counted once, including a blank line; each partial chunk counts once. Input longer than the byte limit can produce several rejected chunks, each using one budget entry. Unless that reaches the budget, a later empty read causes a timeout.

**Reread:** pySerial Short introduction, “Readline” (why a timeout is essential) and URL handlers, “loop://”.

### E5 — SPI, I2C, UART, and communication settings (easy, ~7 min)

**Goal:** Check a connection for a new avionics box (aircraft or spacecraft electronics) on the bench. Compare SPI, I2C, and UART, then diagnose mismatched settings using the readings above.

**Signature:** `def bus_answers() -> dict[str, str]`

Return a dictionary with exactly the keys `"Q1"`, `"Q2"`, `"Q3"`, `"Q4"`, and `"Q5"`. Each value is the uppercase letter of your chosen option (`"A"`, `"B"`, `"C"`, or `"D"` where offered). Choose one option per question. This is a reading check; no connection or hardware is needed.

**Example:** `sorted(bus_answers())` → `["Q1", "Q2", "Q3", "Q4", "Q5"]`. `sorted` returns the dictionary's keys in order; the values are your answer letters.

**Q1.** The box sends serial data asynchronously: there is no shared clock wire carrying a repeating timing signal between sender and receiver. Which interface is this?

- A. SPI (Serial Peripheral Interface)
- B. I2C (Inter-Integrated Circuit)
- C. UART

<details>
<summary>Why it matters on the job</summary>

Recognizing the timing scheme helps you choose the right bench connection.
</details>

**Q2.** A standard USB (Universal Serial Bus) to serial adapter appears as `/dev/ttyUSB0` on the Linux test PC and connects to the box's TX/RX pins (transmit/receive). The box uses 115200 baud but the adapter uses 9600; which pair describes the box-side interface and a likely received result?

- A. UART; readable replies arriving more slowly
- B. UART; a missing device address (a number selecting the receiver)
- C. UART; garbled received bytes or framing errors (the receiver misses the expected stop bit)
- D. UART; readable replies because the adapter automatically matches the box's baud

<details>
<summary>Why it matters on the job</summary>

Checking communication settings early can save hours of debugging valid device software.
</details>

**Q3.** You are checking how a bench computer selects a chip and times its bits; which description matches conventional SPI, I2C, and UART?

- A. SPI uses a shared clock and device addresses; I2C uses a shared clock and a chip-select for each chip; UART has no shared clock.
- B. SPI uses a shared clock and a chip-select for each chip; I2C uses a shared clock and device addresses; UART has no shared clock or built-in device addressing.
- C. SPI has no shared clock and selects chips by address; I2C uses a shared clock and device addresses; UART requires a shared clock and a chip-select.

<details>
<summary>Why it matters on the job</summary>

The selection and timing scheme determines which bench signals you need to inspect.
</details>

**Q4.** For one connected chip, use conventional SPI with separate send/receive data lines and one chip-select, conventional I2C, and UART TX/RX without extra flow-control wires (signals that pause transmission). Counting signal wires only, which counts and duplex capabilities match these connections?

- A. SPI: 3 wires, half-duplex; I2C: 2 wires, half-duplex; UART: 2 wires, full-duplex.
- B. SPI: 4 wires, full-duplex; I2C: 2 wires, full-duplex; UART: 2 wires, full-duplex.
- C. SPI: 4 wires, full-duplex; I2C: 2 wires, half-duplex; UART: 2 wires, half-duplex.
- D. SPI: 4 wires, full-duplex; I2C: 2 wires, half-duplex; UART: 2 wires, full-duplex.

<details>
<summary>Why it matters on the job</summary>

Wire counts and direction of data flow help you check wiring against its intended connection.
</details>

**Q5.** An **ADC** (analog-to-digital converter) turns a sensor voltage into a digital number, a **configuration chip** stores settings, and an instrument **console** accepts text commands and returns replies. Which is a typical pairing on an avionics bench, subject to each device's data sheet (its technical specification)?

- A. SPI for sensors and ADCs; I2C for small configuration chips; UART for instrument consoles.
- B. SPI for instrument consoles; I2C for sensors and ADCs; UART for small configuration chips.
- C. SPI for small configuration chips; I2C for instrument consoles; UART for sensors and ADCs.

<details>
<summary>Why it matters on the job</summary>

Recognizing common device connections helps you choose a useful starting point before checking the data sheet.
</details>

**Watch out:** Use question IDs as keys, not bus names. Return letters, not option text. Both sides must use compatible settings; readable text is not guaranteed when they disagree.

**Reread:** SparkFun Serial Communication, “Synchronous vs. Asynchronous”, “Baud Rate” and “UARTs”; SparkFun Serial Peripheral Interface (SPI), signal wiring and chip selection; SparkFun I2C, hardware wiring and addressing. Use the SPI and I2C introductions for typical device uses.
