# d23 — Binary packets with struct and CRC

**Time:** about 60 minutes · **Read first:** [struct: byte order, sizes and format characters](https://docs.python.org/3/library/struct.html), [tcpdump: reading captures (-r, -n, port filters)](https://www.tcpdump.org/manpages/tcpdump.1.html), [zlib.crc32](https://docs.python.org/3/library/zlib.html#zlib.crc32), [PyVISA: Reading and writing values (binary values section)](https://pyvisa.readthedocs.io/en/latest/introduction/rvalues.html#reading-binary-values), and [Endianness: overview](https://en.wikipedia.org/wiki/Endianness) · **You edit:** `starter/packets.py`

## What you're building

A chassis test station receives telemetry: measurements sent from a device to the station. You'll encode and check the same binary packet format used in capstone block 4, then recover complete packets from a saved stream containing damaged data and stray bytes. This lets an operator inspect readings without silently accepting corrupted measurements.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/packets.py`. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: d23** (or run `bash tools/run.sh d23` / `tools\run.ps1 d23`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **byte** holds 8 bits (binary digits); Python's `bytes` is an immutable sequence of byte values from 0 to 255. A **packet** is one message with a defined byte layout. Its **header** describes the message, its **payload** contains readings, and its **trailer** contains a check value.

- **Endianness** is the order of bytes in a multi-byte number. **Big-endian** puts the most significant byte first; use `>` in a `struct` format to select it with standard sizes and no padding (extra alignment bytes).
- `struct.pack(format, ...)` encodes numbers as bytes; `struct.unpack(format, data)` decodes an exactly sized byte sequence into a tuple. `struct.calcsize(format)` gives the byte count.
- **Unsigned** integers cannot be negative. `u16` means an unsigned 16-bit integer; `f32` means a 32-bit floating-point number, which may round a Python `float`.
- A **sync word** is a fixed byte pattern marking a possible packet start. Here it is `EB 90` in hexadecimal (base 16), written `b"\xeb\x90"` in Python.
- A **CRC** (cyclic redundancy check) is a checksum used to detect damaged bytes. Use `zlib.crc32(data)`; encode its unsigned result in four big-endian bytes. A valid CRC does not prove who sent the data.
- A **stream** is a sequence of bytes that may contain many packets. **Resynchronizing** means looking for the next valid start after a damaged candidate.

For example, this encodes a two-byte instrument code, not the station header:

```python
import struct
encoded = struct.pack(">H", 513)
assert encoded == b"\x02\x01"
(code,) = struct.unpack(">H", encoded)
assert code == 513
```

### Station packet layout

All fields are big-endian. Offsets count bytes from zero.

| Field | Offset | Bytes | Meaning / struct character |
| --- | --- | --- | --- |
| sync | 0 | 2 | Always `0xEB90`; `H` |
| seq | 2 | 2 | Sequence number identifying a message, 0..65535; `H` |
| ts_us | 4 | 8 | Device timestamp in microseconds (millionths of a second), 0..2**64-1; `Q` |
| count | 12 | 1 | Number of readings, 0..255; `B` |
| readings | 13 | 5 × count | Each is channel (`B`, one byte) then value (`f`, four bytes) |
| CRC | 13 + 5 × count | 4 | CRC of every preceding byte, including sync; `I` |

The header format is `>HHQB` (13 bytes), each reading is `>Bf`, and the CRC is `>I`. A complete packet has exactly `17 + 5 * count` bytes. A **channel** is the numeric identifier of one measurement input, 0..255. No channel may appear twice in one packet. Zero readings is valid.

For all exercises, arguments have the annotated Python types. Integer range errors listed below must raise `ValueError`. Reading values supplied to `build_packet` are finite numbers representable as `f32`; handling values outside that domain is not required. Parsing accepts any value that `struct` decodes as `f32`, including infinity and NaN (a floating-point "not a number" value). No timestamp ordering or sequence continuity check is needed here.

`PacketError` is a supplied subclass of `ValueError` for malformed received bytes. Do not change it. Its message is your choice. E1–E4 may reuse earlier functions.

## Exercises

### E1 — Encode the station header (easy, ~9 min)

**Goal:** Give the station encoder and decoder one consistent header layout.

**Signatures:** `def pack_header(seq: int, ts_us: int, count: int) -> bytes` and `def unpack_header(b: bytes) -> tuple[int, int, int]`

`pack_header` returns the 13-byte header including sync. Raise `ValueError` when seq, ts_us, or count is outside its table range. `unpack_header` accepts exactly 13 bytes, verifies sync, and returns `(seq, ts_us, count)` without the sync word. Raise `PacketError` for any other length or bad sync.

**Example:** `pack_header(1, 2, 1).hex()` → `"eb900001000000000000000201"`; unpacking those bytes → `(1, 2, 1)`.

**Watch out:** Native byte order and alignment vary by computer. Do not use the default `struct` byte order. Pass only a header slice to `unpack_header`, not a full packet.

**Reread:** struct, “Byte Order, Size, and Alignment” and “Format Characters”; Endianness, overview.

### E2 — Build a checked measurement packet (medium, ~11 min)

**Goal:** Encode readings for a station telemetry transmitter.

**Signature:** `def build_packet(seq: int, ts_us: int, readings: dict[int, float]) -> bytes`

Return header + readings + CRC using the table. Emit channels in ascending numeric order regardless of dictionary insertion order. Count is `len(readings)`. Raise `ValueError` for invalid seq or ts_us, more than 255 readings, or any channel outside 0..255. Do not change the input dictionary.

**Example:** `build_packet(1, 2, {3: 1.5})` is 22 bytes: the E1 example header, reading bytes `03 3f c0 00 00`, then the four-byte CRC of those first 18 bytes. `build_packet(0, 0, {})` is 17 bytes.

**Watch out:** The CRC covers the header and payload, but not the CRC itself. Sorting channel numbers makes the byte output repeatable.

**Reread:** struct, “Format Characters” (`B`, `f`, `I`); zlib.crc32, its data argument and unsigned return value.

### E3 — Validate incoming station telemetry (medium, ~13 min)

**Goal:** Reject damaged device data before it reaches station result checks.

**Signature:** `def parse_packet(b: bytes) -> tuple[int, int, dict[int, float]]`

Return `(seq, ts_us, readings)`. Raise `PacketError` for fewer than 17 bytes, bad sync, a total length different from `17 + 5 * count` (including extra trailing bytes), a CRC mismatch, or a duplicate channel. Check the stored CRC against every byte before it. The order of validation and dictionary insertion is your choice. Accept channels in any wire order; only the builder must sort them.

**Example:** `parse_packet(build_packet(7, 100, {2: 1.5}))` → `(7, 100, {2: 1.5})`.

**Watch out:** Check lengths before unpacking slices, so malformed input raises `PacketError`, not `struct.error`. A value such as 0.1 rounds in `f32`; do not round decoded values again. A duplicate channel remains invalid even if its CRC is correct.

**Reread:** struct, `unpack`, `unpack_from` and “Format Characters” (`f`); zlib.crc32.

### E4 — Recover packets from a station byte log (medium, ~12 min)

**Goal:** Let an operator recover complete valid messages despite junk or damaged packets in a byte log.

**Signature:** `def find_packets(stream: bytes) -> list[bytes]`

Scan left to right for sync bytes `EB 90`. For each candidate with a complete header, read count and consider exactly `17 + 5 * count` bytes. Accept the candidate only if `parse_packet` accepts it. Append the original packet bytes and resume immediately after that packet. After any invalid or incomplete candidate, resume scanning one byte after its starting position, so a later valid packet inside that rejected candidate is still found. A lone trailing sync byte is ignored. Return `[]` if nothing valid is found; damaged stream contents must not raise `PacketError`.

**Example:** if `p = build_packet(1, 2, {})`, then `find_packets(b"noise" + p + b"junk" + p)` → `[p, p]`. Preserve repeated packets and their stream order. Ignore a sync pattern inside an accepted packet's payload.

**Watch out:** Do not stop at an incomplete candidate: its count might be damaged, with a valid packet later in the remaining bytes. This function receives raw station bytes, not a capture file with network headers.

A **capture** is a saved record of network traffic. **tcpdump** inspects those records; a **port** identifies a network endpoint. For operator investigation, `tcpdump -r station.pcap -n 'udp port 9000'` reads an existing capture (`-r`), displays numeric addresses and ports (`-n`), and filters UDP traffic involving port 9000. UDP is the User Datagram Protocol, which sends separate network messages. This command is reading context only; these tests need no capture, tcpdump installation, or live network.

**Reread:** tcpdump, OPTIONS (`-r`, `-n`) and EXPRESSIONS (port filters); struct, `unpack_from` for reading a header at an offset.

### E5 — Decode an oscilloscope waveform block (medium, ~15 min)

**Goal:** Turn an oscilloscope reply into sample values for a station measurement check. An **oscilloscope** records a **waveform**, a sequence of sampled signal values. The instrument commands `CURV?` and `WAV:DATA?` request those values. The reply uses the IEEE 488.2 instrument-message standard's **definite-length block**, whose header states exactly how many data bytes follow.

**Signature:** `def parse_block(reply: bytes, fmt: str = "h", big_endian: bool = True) -> list[int | float]`

**ASCII** is a character encoding; here digits mean only the byte characters `0` through `9`. Read the reply from its first byte using this layout:

| Part | Meaning |
| --- | --- |
| `#` | Required first byte |
| `n` | One ASCII digit from `1` to `9`: how many count digits come next |
| count digits | Exactly `n` ASCII digits giving the number of data bytes |
| data | Exactly that many bytes, containing consecutive sample values |
| optional `\n` | At most one newline byte (byte value 10) after the data |

The count is a byte count, not a sample count. Leading zeros in the count are valid. A count of zero is valid and returns `[]`; `#0` instead selects an **indefinite-length block** (no explicit byte count), which this exercise rejects.

Decode the data with `struct` and return a list in sample order. `fmt` must be exactly one character from this table. **Signed** integers can be negative.

| `fmt` | Sample type | Bytes per sample |
| --- | --- | --- |
| `"b"` | Signed integer | 1 |
| `"B"` | Unsigned integer | 1 |
| `"h"` | Signed integer | 2 |
| `"H"` | Unsigned integer | 2 |
| `"f"` | Floating-point number (`f32`) | 4 |

Use big-endian (`>`) when `big_endian` is `True`. Otherwise use **little-endian** (`<`), which puts the least significant byte first. Return Python `int` values for the integer formats and `float` values for `"f"`; preserve the values decoded by `struct` without rounding them again.

Raise `ValueError` with a clear message for a missing `#`, a missing or non-digit `n`, `n = 0`, missing or non-numeric count digits, fewer data bytes than declared, any extra bytes other than the one optional newline, an unsupported `fmt`, or a data length that is not a multiple of the sample size. The order of validation is your choice.

**Example:** `parse_block(b"#14\x00\x01\xff\xfe\n")` → `[1, -2]`. Here `n = 1`, the next digit declares four data bytes, and each `"h"` sample takes two bytes. `parse_block(b"#14\x01\x00\xfe\xff", big_endian=False)` → `[1, -2]` too. `parse_block(b"#10")` → `[]`.

**Watch out:** Locate the data's end using the declared count before checking the optional newline. A newline inside those data bytes is a sample byte: `parse_block(b"#11\n", fmt="B")` and `parse_block(b"#11\n\n", fmt="B")` both return `[10]`. Do not strip whitespace from the reply or let malformed slices leak `IndexError` or `struct.error`.

**Reread:** struct, "Byte Order, Size, and Alignment", "Format Characters", `calcsize` and `unpack`; PyVISA, "Reading and writing values", "Reading binary values" (the IEEE block header and termination character).
