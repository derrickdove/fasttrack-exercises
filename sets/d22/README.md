# d22 — Serial devices with pyserial

**Time:** about 55 minutes · **Read first:** [SparkFun: Serial Communication](https://learn.sparkfun.com/tutorials/serial-communication/all) (baud, framing, UART); [SparkFun: Serial Peripheral Interface (SPI)](https://learn.sparkfun.com/tutorials/serial-peripheral-interface-spi/all); [SparkFun: I2C](https://learn.sparkfun.com/tutorials/i2c/all); [pySerial: Short introduction](https://pyserial.readthedocs.io/en/latest/shortintro.html) and [URL handlers: loop://](https://pyserial.readthedocs.io/en/latest/urlhandler.html#loop); [Linux device management: udev overview](https://en.wikipedia.org/wiki/Udev) · **You edit:** `starter/serial_sensor.py`

## What you're building

A chassis test station reads temperature and pressure from a serial sensor. You will open a simulated connection, exchange complete lines, check each measurement's checksum, and count damaged messages without losing good readings. Everything runs without hardware on Windows or Linux.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/serial_sensor.py`. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: d22** (or run `bash tools/run.sh d22` / `tools\run.ps1 d22`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **serial connection** carries bits one after another. A **UART** (universal asynchronous receiver/transmitter) converts bytes to serial signals; **baud** measures signal changes per second. **8N1** means eight data bits, no parity bit (an extra error-checking bit), and one stop bit. pySerial defaults to 9600 baud and 8N1; keep those defaults here.

A **port** is the connection object. A **timeout** bounds how long a read or write waits, in seconds. A **URL handler** selects a connection from a string: `loop://` is a software **loopback**, which returns bytes written to it. It needs no physical device. On Linux a USB serial adapter often appears as `/dev/ttyUSB0`; the `dialout` group commonly grants access, and **udev** manages device nodes (files representing devices), permissions, and stable names. You do not change Linux settings in this set.

**ASCII** encodes basic text as bytes. **Framing** marks message boundaries: **CRLF**, `\r\n`, is carriage return followed by line feed. `port.write(...)` takes bytes; `port.readline()` returns bytes through the next `\n`, or partial/empty bytes when its timeout expires. `encode("ascii")` converts text to bytes; `decode("ascii")` reverses it. A **buffer** holds bytes waiting to be read.

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
- `read_line` calls `port.readline()` once. If it returns `b""`, raise `TimeoutError`. If the returned bytes do not end in `b"\r\n"`, raise `ValueError`. Otherwise remove exactly those final two bytes and decode ASCII; non-ASCII bytes raise `ValueError` (Python's `UnicodeDecodeError` is a subclass of it). Preserve spaces and other payload characters.

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

### E4 — Collect good station frames (medium, ~10 min)

**Goal:** Reuse E2 and E3 to collect `count` valid measurement dictionaries, in arrival order. Skip any line for which either helper raises `ValueError`, and add one to `bad` for that line. Return `(frames, bad)` when you have exactly `count` good frames. Corrupted lines do not use up the requested good-frame count.

**Signature:** `def read_frames(port: serial.Serial, count: int) -> tuple[list[dict[str, float]], int]`

**Example:** Given a bad-checksum line, then `$TMP,23.5,PRS,101.2*02`, requesting one frame returns `([{"TMP": 23.5, "PRS": 101.2}], 1)`.

**Watch out:** `count` is an integer. Zero returns `([], 0)` without reading; a negative count raises `ValueError` without reading. Stop immediately after enough good frames so later bytes remain unread. Let `TimeoutError` and connection errors propagate; do not retry silence forever or return partial results on timeout. Keep the port open. A bad complete line is counted once, including a blank line; a partial line counts once before a later empty read causes a timeout.

**Reread:** pySerial Short introduction, “Readline” (why a timeout is essential) and URL handlers, “loop://”.

### E5 — UART, SPI and I2C (easy, ~10 min)

**Goal:** Choose a connection for a new avionics box (aircraft or spacecraft electronics) on the bench. A **bus** is a set of wires and communication rules connecting devices. Alongside UART, compare **SPI** (Serial Peripheral Interface) and **I2C** (Inter-Integrated Circuit) using the readings above.

**Signature:** `def bus_answers() -> dict[str, str]`

Return a dictionary with exactly the keys `"Q1"` through `"Q5"`. Each value is the uppercase letter of your chosen option (`"A"`, `"B"`, `"C"`, or `"D"` where offered). Choose one option per question. This is a reading check; no connection or hardware is needed.

**Example:** `sorted(bus_answers())` → `["Q1", "Q2", "Q3", "Q4", "Q5"]`. `sorted` returns the dictionary's keys in order; the values are your answer letters.

**Q1.** The box sends serial data asynchronously: there is no shared clock wire carrying a repeating timing signal between sender and receiver. Which interface is this?

- A. SPI
- B. I2C
- C. UART

<details>
<summary>Why it matters on the job</summary>

Recognizing the timing scheme helps you choose the right bench connection.
</details>

**Q2.** Several devices share data and clock wires, but each has its own **chip-select** line (a wire that activates that device for a transfer). Which bus normally uses this arrangement?

- A. I2C
- B. SPI
- C. UART

<details>
<summary>Why it matters on the job</summary>

Selecting the wrong device can send a valid command to the wrong box.
</details>

**Q3.** A sensor connection has two signal wires, clock and data, plus a common ground (the shared voltage reference). Transfers use a device **address** (a number selecting the receiver) and **ACK** (an acknowledgment signal that a byte was received); which bus is it?

- A. I2C
- B. UART
- C. SPI

<details>
<summary>Why it matters on the job</summary>

Understanding how a sensor is selected and confirms receipt helps locate a failed transfer.
</details>

**Q4.** The station must send commands while receiving data at the same time, called **full duplex**. Which pair supports this with separate send and receive data wires in the usual wiring?

- A. UART and I2C
- B. UART and SPI
- C. SPI and I2C

<details>
<summary>Why it matters on the job</summary>

Knowing whether traffic can flow both ways at once prevents incorrect timing assumptions.
</details>

**Q5.** A standard USB (Universal Serial Bus) to serial adapter appears as `/dev/ttyUSB0` on the Linux test PC and connects to the box's TX/RX pins (transmit/receive). The box uses 115200 baud but the adapter uses 9600; which pair describes the box-side interface and a likely received result?

- A. UART; readable replies arriving more slowly
- B. I2C; a missing address acknowledgment
- C. UART; garbled received bytes or framing errors (the receiver misses the expected stop bit)
- D. SPI; a missing chip-select signal

<details>
<summary>Why it matters on the job</summary>

Checking communication settings early can save hours of debugging valid device software.
</details>

**Watch out:** Use question IDs as keys, not bus names. Return letters, not option text. Both sides must use compatible settings; readable text is not guaranteed when they disagree. The question about full duplex asks for a pair, since more than one interface supports it.

**Reread:** SparkFun Serial Communication, “Synchronous vs. Asynchronous”, “Half/Full-Duplex”, “Baud Rate” and “UARTs”; the SPI tutorial's chip-select and data-signal discussions; the I2C tutorial's address and ACK message discussion.
