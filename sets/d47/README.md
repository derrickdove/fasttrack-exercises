# d47 — Reading C: registers, bits and structs

**Time:** about 53 minutes (5 minutes to orient, then 48 minutes of exercises) · **Read first:** learncpp O.2, [Bitwise operators](https://www.learncpp.com/cpp-tutorial/bitwise-operators/), and O.3, [Bit manipulation with bitwise operators and bit masks](https://www.learncpp.com/cpp-tutorial/bit-manipulation-with-bitwise-operators-and-bit-masks/); learncpp 13.7, Introduction to structs; *C++ Primer*, chapter 4, the section on bitwise operators (your book; read for understanding, you won't write C++ until tomorrow); Wikipedia, [Endianness](https://en.wikipedia.org/wiki/Endianness) · **You edit:** `starter/registers.py`

## What you're building

A chassis test station needs to interpret a power supply unit (PSU) driver's status and configuration. A driver is software that communicates with an instrument. You will read the supplied C header, `data/psu_regs.h`, and implement its behavior in Python so an operator can see flags, configure bits, and inspect a received status frame (one message with a fixed byte layout). You will also translate five lines from driver code into plain English; no C compiler or hardware is needed.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/registers.py`. Don't edit `tests/`, `data/psu_regs.h`, or the supplied answer choices.
2. Press **Ctrl+Shift+B → Test: d47** (or run `bash tools/run.sh d47` / `tools\run.ps1 d47`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **header** (`.h`) describes C names and data layouts; `#define` gives a name to a value or expression. A **register** is a small hardware storage location represented here by an integer. A **bit** is a binary digit, 0 or 1; a **byte** has eight bits, numbered 0 through 7 from right to left. **Hexadecimal** (prefix `0x`) writes numbers in base 16; **binary** (prefix `0b`) writes them in base 2.

A **mask** selects bit positions with 1s. A **flag** is a bit used as a yes/no condition. Bitwise operators act on individual bits: `&` selects shared 1s, `|` combines 1s, `~` flips bits, and `<<` / `>>` shift bits left / right. Python integers have no fixed bit width, so `~` can produce a negative number. A **field** is a group of adjacent bits used as one number; its **shift** counts lower bits and its **width** counts its bits.

```python
sample = 0b00101000
print(sample >> 3)          # 5: move the bits three places right
print(bool(sample & 0x08))  # True: bool turns a nonzero value into True
print(hex(0b10000000))      # '0x80': another way to write the same integer
```

A **struct** groups named values called **members**. **Packed** means members have no unused padding bytes between them. **Endianness** is the order of bytes in a multi-byte number; little-endian puts the lowest-value byte first. **Unsigned** integers cannot be negative; **signed** integers can. The header defines the frame's signed encoding and units. Python's `struct.unpack` decodes binary layouts (`<` selects little-endian without padding; `B` is an unsigned byte, `H` an unsigned two-byte integer, `h` a signed two-byte integer). Alternatively, `int.from_bytes` decodes a byte slice with an explicit byte order and `signed` setting.

A **pointer** holds the location of another value. **Dereferencing** reads or writes the value at that location (`*ptr`). The `->` operator selects a struct member through a pointer. A **cast** such as `(uint8_t)` converts a value to a named type; `uint8_t` is an unsigned eight-bit integer. **Volatile** marks a value that can change independently, such as a hardware register, so the compiler must perform the specified reads.

All numeric arguments in E1/E2 are Python integers; other types are outside this set's contract. Invalid numeric ranges must raise `ValueError`; the message is your choice. Do not silently clamp values or wrap them around.

## Exercises

### E1 — Show the PSU status flags (easy, ~8 min)

**Goal:** Turn the station's status byte into four operator-visible flags, using the `PSU_...` masks in `data/psu_regs.h`.

**Signature:** `def decode_status(byte: int) -> dict[str, bool]`

Return exactly the four keys written beside the header's status masks. Each value must be a Python `bool`: `True` if that mask's bit is 1, otherwise `False`. Include inactive flags too. Ignore reserved bits (bits with no assigned meaning); dictionary order does not matter. A byte outside `0..255` raises `ValueError`.

**Example:** `decode_status(0)` → `{"ready": False, "output_on": False, "overcurrent": False, "overtemp": False}`

**Watch out:** A mask value such as `16` is an integer, not the boolean `True` required for the operator view. Use the header for bit positions; the four flags are not adjacent.

**Reread:** learncpp O.2, bitwise AND; O.3, checking whether a bit is on. Then read the status-mask comments in `data/psu_regs.h`.

### E2 — Change configuration bits and read a field (easy/medium, ~10 min)

**Goal:** Update a PSU configuration register without disturbing unrelated settings, then extract its selected range field.

**Signatures:**

```python
def set_bits(reg: int, mask: int) -> int
def clear_bits(reg: int, mask: int) -> int
def field(reg: int, shift: int, width: int) -> int
```

`set_bits` returns a register with every bit selected by `mask` set to 1. `clear_bits` returns a register with every selected bit set to 0. All other bits stay unchanged. Both operands must be in `0..255`, or raise `ValueError`. A zero mask changes nothing; all eight bits may be selected.

`field` returns the unsigned number in `width` adjacent bits starting at bit `shift`, moved down so its lowest bit becomes bit 0. Require `0 <= reg <= 255`, `0 <= shift <= 7`, `1 <= width <= 8`, and `shift + width <= 8`; otherwise raise `ValueError`. It must work for every valid field, including the range field named in the header.

**Examples:** `set_bits(0x20, 0x03)` → `0x23`; `clear_bits(0x23, 0x03)` → `0x20`; `field(0b10101100, 2, 3)` → `3`.

**Watch out:** Clearing bits must still return an integer in `0..255`. Extract only the chosen field, excluding higher bits. These functions return new integers and do not access real hardware.

**Reread:** learncpp O.2, bitwise NOT and shifts; O.3, setting and clearing bits; *C++ Primer*, chapter 4, bitwise operators. Read the configuration-field comments in the header.

### E3 — Decode the packed station frame (medium, ~15 min)

**Goal:** Turn the PSU's received bytes into the measurements and counter described by `struct status_frame` in the header.

**Signature:** `def unpack_status_frame(b: bytes) -> dict[str, int]`

Accept a `bytes` object of exactly seven bytes. Return exactly the member names shown in the header as dictionary keys, with integer values using the documented offsets, widths, signedness, and byte order. Preserve the raw status integer and the original units. All possible field values are valid, including reserved status bits and the counter's maximum value. If the length is shorter or longer than seven, raise `ValueError` (do not expose `struct.error`). Dictionary order does not matter; other input types are outside the contract.

**Example:** `unpack_status_frame(b"\x01\xe0\x2e\xfa\x00\x02\x00")` → `{"status": 1, "voltage_mv": 12000, "current_ma": 250, "sequence": 2}`.

**Watch out:** The current can be negative. Do not assume your computer's native layout matches the frame. The header's `#pragma pack` directives request no padding; each member begins immediately after the previous one.

**Reread:** learncpp 13.7, Introduction to structs, especially members; *C++ Primer*, chapter 4, shifts and masks if decoding byte slices manually. Read the entire packed-frame comment in `data/psu_regs.h`.

### E4 — Explain five driver lines (easy, ~7 min)

**Goal:** Help the next station maintainer read C driver code. Match each supplied C line to its meaning without executing it.

**Signature:** `def explain(line: str) -> str`

The five valid inputs are in the supplied `C_LINES` tuple (an ordered, unchangeable collection) in `starter/registers.py` and are repeated on the header's reading cards. The header supplies the types and meaning of each variable. Return the matching string from `MEANINGS`, copied exactly, including punctuation. Every choice is used by exactly one valid input. Do not change these supplied collections. A lookup dictionary is sufficient; you do not need to parse C.

Only exact input strings are accepted: any other string, including an empty string or a valid line with extra whitespace, must raise `ValueError`. These are independent snippets; the assignment to `value` stores the result, while the assignment through a pointer writes to the pointed-to location.

**Example:** `explain("value = *status_ptr;")` → `"Read the byte that status_ptr points to into value."`

**Watch out:** One card writes a byte; the others read or convert values. On the cast card, conversion keeps the lowest eight bits of `raw`. On the hardware card, `status_reg` points to a volatile byte even though the word `volatile` is in the supplied context rather than on the line itself.

**Reread:** learncpp 13.7, member selection; *C++ Primer*, chapter 4, bitwise operators, for the cast's lowest-eight-bits effect. Use the pointer, cast, and volatile definitions above and the header's E4 context; no additional pointer chapter is required today.

### E5 — Byte order on the wire (QUIZ, easy, ~8 min)

**Goal:** Choose the right byte order when the station receives telemetry (measurements sent from a device).

**Signature:** `def endian_answers() -> dict[str, str]`

Return a dictionary with exactly the keys `"Q1"`, `"Q2"`, `"Q3"`, and `"Q4"`. Each value is the uppercase letter of your chosen option, such as `"A"`; return one answer per question. Dictionary order does not matter.

A 16-bit integer occupies two bytes. **Big-endian** puts the highest-value byte first; **little-endian** puts the lowest-value byte first. In memory, "first" means the lower memory address (the numbered location of a byte); on the wire, it means the byte sent first. Byte pairs below are written in hexadecimal. Byte order changes the order of whole bytes, not the bits inside each byte.

**Q1.** A PSU driver stores the 16-bit value `0x1234` in big-endian memory. Which bytes appear from the lower address to the higher address?

- A. `34 12`
- B. `12 34`
- C. `00 12 00 34`
- D. `21 43`

<details>
<summary>Why it matters on the job (Q1)</summary>

Reading a memory dump (a list of stored bytes) helps you compare the driver's value with the device's specification.
</details>

**Q2.** A network protocol (agreed rules for exchanging data) says a telemetry field uses "network byte order." Which byte order does that mean?

- A. The sending computer's native byte order (its default order for storing numbers).
- B. The receiving computer's native byte order.
- C. Little-endian.
- D. Big-endian.

<details>
<summary>Why it matters on the job (Q2)</summary>

A shared format lets test stations exchange measurements across different kinds of computers.
</details>

**Q3.** You are inspecting native memory on an x86 test PC or most ARM test PCs; x86 and ARM are processor families, and PC means personal computer. Which byte order do these machines normally use?

- A. Little-endian.
- B. Big-endian.
- C. Whichever byte order the connected instrument uses.

<details>
<summary>Why it matters on the job (Q3)</summary>

Knowing the station's memory layout helps you investigate differences between stored and received data.
</details>

**Q4.** A big-endian unsigned telemetry field containing `0x0102` arrives as `b"\x01\x02"`. On a little-endian PC, what does `struct.unpack("<H", b"\x01\x02")[0]` produce?

- A. `0x0102` = 258, because Python detects the sender's byte order.
- B. It raises `struct.error` (a binary-format error) because the sender and PC use different byte orders.
- C. `0x0201` = 513, because the bytes are interpreted in the opposite order.

<details>
<summary>Why it matters on the job (Q4)</summary>

A decoding mistake can turn a valid measurement into a misleading limit failure.
</details>

**Example (worked):** This different telemetry value shows the same two bytes decoded in two ways. `>` selects big-endian; `<` selects little-endian; `H` is an unsigned two-byte integer. `unpack` returns a tuple, so `[0]` selects its first (and here only) value.

```python
import struct

wire = b"\x03\x04"  # the big-endian encoding of 0x0304
print(struct.unpack(">H", wire)[0])  # 772
print(struct.unpack("<H", wire)[0])  # 1027
```

**Watch out:** An explicit `<` or `>` tells `struct` how to interpret the bytes regardless of the PC's native byte order. Follow the device's field specification; the E3 frame and another device's telemetry can use different orders.

**Reread:** Wikipedia, *Endianness*, the opening definition and the "Overview", "Hardware", and "Networking" sections; use the day's bitwise and struct readings to review how two bytes form one number.
