# r4 — Week 4 review: a telemetry capture at the bench

**Time:** about 60 minutes · **Read first:** no new reading; revisit d04 (CSV), d12 (grouped reports), d17 (fake transports), d18 (cleanup), and review d22–d27: Python "Socket Programming HOWTO" (datagrams and framing), Beej's Guide (datagram sockets), `socket` docs (`SOCK_DGRAM`, `sendall`), `struct` docs (byte order and format characters), `zlib.crc32` docs, Wikipedia "Endianness" and "Serial number arithmetic", RFC 1982 section 3 (optional), `collections.deque` docs, Wireshark wiki "Libpcap File Format", tcpdump man page (`-r` and filters), Wireshark User's Guide "Capturing", `threading` docs (`Thread`, `Event`), `queue` docs, and The Pragmatic Programmer's concurrency topic (optional). · **You edit:** `starter/review4.py`

## What you're building

A chassis test station receives **telemetry**, measurements sent automatically by hardware; this set mixes this week's telemetry work with earlier weeks' CSV files, grouped failure reports, and instrument call sequences. A replacement sensor board uses a different binary packet format, and the operator wants to know whether its saved traffic has missing readings. Build its encoder, decoder, stream buffer, and capture report without connecting to hardware.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/review4.py`. Don't edit `tests/`, the supplied helpers, or `data/`.
2. Press **Ctrl+Shift+B → Test: r4** (or run `bash tools/run.sh r4` / `tools\run.ps1 r4` from the repo root). At first you'll see `Exercises: 0 / 7 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **byte** holds an integer from 0 through 255; `bytes` is an immutable sequence of bytes. A **packet** is one complete encoded message. **UDP** sends individual messages called **datagrams**, while **TCP** sends a continuous byte stream whose reads may split or combine messages. **Framing** means marking where each message starts and ends in that stream.

**Hexadecimal** writes numbers in base 16 (`0x` marks such an integer). **Little-endian** stores the least significant byte first: integer 258 occupies `b"\x02\x01"` in two bytes. A **signed** integer can be negative; an **unsigned** integer cannot. Python's `struct` module converts numbers to and from bytes. Its `<` prefix selects little-endian with no padding; `B` is one unsigned byte, `H` is an unsigned two-byte integer, `h` is a signed two-byte integer, and `2s` is two literal bytes. Here is a different station field:

```python
import struct
encoded = struct.pack("<H", 258)
assert encoded == b"\x02\x01"
(decoded,) = struct.unpack("<H", encoded)
assert decoded == 258
```

A **CRC** (cyclic redundancy check) is a number computed from bytes to detect corruption. `crc16(data)` is supplied: it returns a 16-bit integer using the station's CRC-16/CCITT-FALSE algorithm. Do not implement the CRC algorithm. The check example is `crc16(b"123456789") == 0x29b1`. This variant uses CRC-16 rather than d23's CRC-32.

A `bytearray` is a byte buffer you can change; `buffer.extend(chunk)` appends bytes. A **sequence number** labels a packet's position; after 65535 comes 0, called **wraparound**. A **capture** saves network traffic to a file. **pcap** is a common capture file format containing network frames (raw network messages) and timestamps. The supplied `capture_payloads` helper extracts the UDP **payload**, the application bytes inside a datagram; you do not implement a pcap reader today. A destination **port** is the integer used to direct a datagram to the receiving application.

For E1-E5, numeric inputs have the integer types in the signatures; you only validate the ranges below. Do not mutate caller dictionaries or lists. Work in arrival order throughout.

## Packet format for E1 and E2

A **channel** identifies one measurement input. This format is local to this review. All multi-byte numbers, including the CRC, are little-endian. There is no timestamp or floating-point field.

| Byte offset (starting at 0) | Field | Format / rule |
| --- | --- | --- |
| 0 | Sync marker (fixed bytes identifying this format) | `b"\xc3\x5a"`, exactly two bytes |
| 2 | Sequence number | `H`, 0–65535 |
| 4 | Reading count | `B`, 0–8 |
| 5 onward | That many reading records | Each record is `<Bh`: channel 1–32, then signed millivolts -32768 to 32767 |
| After the records | CRC | `H`, `crc16` of every preceding byte, starting with sync |

A **millivolt** is one thousandth of a volt. Each channel may appear only once per packet. Total length is exactly `7 + 3 * count` bytes (7–31 bytes). Zero readings is valid. There are no extra bytes or padding. Encoders sort channel numbers; decoders accept any record order.

## Exercises

### E1 — Encode the replacement sensor's packet (easy, ~8 min)

**Goal:** Build the bytes the station expects from a set of millivolt readings.

**Signature:** `def build_packet(seq: int, readings: dict[int, int]) -> bytes`

`readings` maps channel numbers to integer millivolts. Validate the sequence, count, channel, and millivolt ranges in the table; raise `ValueError` on any violation. Emit the header, records sorted by channel number ascending, then the two-byte CRC. Return a new `bytes` object.

**Example:** `build_packet(0x1234, {7: -250, 2: 1200})` starts with `bytes.fromhex("c3 5a 34 12 02 02 b0 04 07 06 ff")` and ends with the little-endian CRC of those 11 bytes. It is 13 bytes long.

**Watch out:** A channel number is unsigned, but a negative reading uses signed `h`. Do not alter the input dictionary's values or insertion order. Use the supplied `crc16`.

**Reread:** d23 — `struct` docs, byte order and format characters; Wikipedia "Endianness"; compare d23's `zlib.crc32` reading with the supplied CRC-16 helper.

### E2 — Reject malformed sensor packets (medium, ~10 min)

**Goal:** Decode exactly one complete packet, keeping corrupted readings out of station results.

**Signature:** `def parse_packet(packet: bytes) -> tuple[int, dict[int, int]]`

Return `(sequence, readings)` with integer millivolts. Accept records in any order. Raise `ValueError` if the packet is shorter than 7 bytes, has the wrong sync, count above 8, a length other than `7 + 3 * count`, a mismatched CRC, a channel outside 1–32, or a repeated channel. Trailing bytes are an error. Use the same packet format and CRC coverage as E1. The encoded field types already constrain sequence and reading values.

**Example:** `parse_packet(build_packet(5, {2: -250}))` → `(5, {2: -250})`; `parse_packet(b"")` raises `ValueError`.

**Watch out:** Validate length before unpacking fields. Malformed input must produce `ValueError`, rather than leaking `struct.error`. Tests supply their own packets, so you can solve E2 before E1.

**Reread:** d23 — `struct` docs (`unpack`, byte order and exact sizes); the CRC checks from that day.

### E3 — Buffer the operator's framed stream (easy, ~4 min)

**Goal:** Reassemble operator messages even when TCP reads split their headers and bodies.

**Signatures:** `FrameBuffer.__init__(self) -> None`; `FrameBuffer.feed(self, chunk: bytes) -> list[bytes]`

To leave time for earlier-week retention, frame extraction is supplied in `extract_frames(pending: bytearray) -> list[bytes]`. It removes complete frames from the passed buffer, keeps unfinished bytes, and implements the oversized-prefix rule below. You only initialize an instance buffer, append each chunk, and return the helper's result. Do not copy or edit the helper.

The frame header is a **length prefix**, a field before the payload. Each frame is a **two-byte unsigned little-endian payload length** followed by that many payload bytes. The length excludes its own two bytes. This differs from d25's four-byte big-endian prefix (most significant byte first). Payloads are arbitrary bytes; do not parse them as telemetry. A zero-length frame is valid. The largest allowed payload is `MAX_FRAME == 4096` bytes, inclusive.

Each new instance starts empty. `feed` appends its chunk, returns all newly complete payloads in order, and retains unfinished bytes for the next call. It returns `[]` if nothing completes. An empty chunk still processes existing bytes. Keep state separate for each instance.

As soon as a complete two-byte prefix says more than 4096, clear **all** buffered bytes and raise `ValueError`, without waiting for the oversized body. This call returns no payloads, even if it decoded some before the bad prefix. The caller can feed a fresh valid frame afterward. No recovery scan or end-of-stream method is required.

**Example:** after `reader = FrameBuffer()`, `reader.feed(b"\x03")` → `[]`, `reader.feed(b"\x00AB")` → `[]`, then `reader.feed(b"C\x00\x00")` → `[b"ABC", b""]`.

**Watch out:** A read can contain half a frame, many frames, or the end of one and start of another. Never assume one read equals one message.

**Reread:** d25 — Python "Socket Programming HOWTO", framing and partial reads; `socket.sendall`. Relate this buffer to the timeout-bounded receive loops from d22 and the listener/queue separation in d27's `threading` and `queue` readings; no sockets or threads are needed in this exercise.

### E4 — Count gaps without being fooled by wraparound (medium, ~10 min)

**Goal:** Summarize sequence numbers from a short station capture.

**Signature:** `def gap_report(seqs: list[int]) -> dict[str, int]`

Reject any sequence outside 0–65535 with `ValueError`. Return exactly these five integer fields:

| Key | Meaning |
| --- | --- |
| `received` | Number of input entries, including repeats and late packets |
| `missing` | Total forward sequence positions skipped when newer packets arrive |
| `duplicates` | Entries whose sequence value has appeared anywhere earlier in this input |
| `out_of_order` | First-time sequence values that are behind the newest accepted value |
| `longest_gap` | Largest number of positions skipped in one forward jump, or 0 |

Start with no newest value and an empty set of seen values. The first entry sets newest, with no inferred loss before it. For each later entry, check for a duplicate first; count it and leave newest unchanged. Otherwise remember it as seen, then compute the **signed serial difference** `delta = (seq - newest + 32768) % 65536 - 32768`. This number lies from -32768 to 32767. If `delta > 0`, count `delta - 1` missing positions, update longest gap, and move newest to this sequence. Otherwise count it as out of order and leave newest unchanged. The exact half-range case (`delta == -32768`) is out of order.

A late packet never subtracts previously counted loss. Remember even late values for later duplicate detection. These are short captures: they do not advance through an entire 65536-value cycle. You can keep every seen value in a set; no duplicate eviction window is required. Empty input returns all five fields as 0.

**Example:** `[65534, 1, 1, 0, 3, 4]` → `{"received": 6, "missing": 3, "duplicates": 1, "out_of_order": 1, "longest_gap": 2}`. The first jump skips 65535 and 0; the later 0 is late and does not repair that gap. The jump from 1 to 3 skips 2.

**Watch out:** Sorting destroys arrival order. A late packet must not move newest backward. This is a report of gaps observed on arrival, not a count of sequence values still absent at the end.

**Reread:** d24 — Wikipedia "Serial number arithmetic", RFC 1982 section 3 (optional), and `collections.deque` docs for comparison with a bounded duplicate history.

### E5 — Report on the captured bench run (medium, ~10 min)

**Goal:** Combine packet validation and gap tracking into an operator report.

**Signature:** `def capture_report(path: Path, port: int) -> dict[str, int]`

First validate the destination port is 0–65535 inclusive; otherwise raise `ValueError` before opening the file. Call the supplied `capture_payloads(path, port)`, which returns matching UDP payloads in capture-file order. Parse each with E2. Count each payload rejected with `ValueError` as one `bad_packets`; leave it out of sequence tracking. Pass valid sequence numbers, including repeats and late arrivals, to E4. Return E4's five fields plus `bad_packets`, with no other keys. Reuse your functions; do not duplicate the decoder or gap logic.

Traffic at other ports is ignored, including malformed telemetry there. No matching datagrams gives six zeros. Missing or unreadable files and malformed pcap containers must propagate their errors from the supplied helper; only per-payload parse errors are counted. The helper raises `ValueError` if the global **snaplen** (maximum captured bytes per frame) is zero, or if a record's captured length exceeds snaplen or its original length (the frame size before capture truncation). No network access or concurrency (running multiple tasks at once) is needed. The helper handles Ethernet → IPv4 (Internet Protocol version 4) → UDP extraction, including IPv4 header options, and skips other traffic and fragmented IP packets (parts of a larger datagram).

**Example:** `capture_report(Path("sets/r4/data/review.pcap"), 5005)` → `{"received": 6, "missing": 3, "duplicates": 1, "out_of_order": 1, "longest_gap": 2, "bad_packets": 2}` when run from the repo root.

The supplied capture contains nine datagrams in file order: port 5005 sequence 65534; port 6006 sequence 4000; port 5005 sequence 1; a bad-CRC packet at 5005; port 5005 sequences 1, 0, 3; a valid-CRC packet with invalid channel 0 at 5005; then port 5005 sequence 4. Valid sensor readings are channel 2 at 1200 millivolts. CRC-invalid and channel-invalid packets do not advance the gap tracker.

**Watch out:** A good CRC does not make an invalid channel acceptable. Catch `ValueError` only around decoding one payload, so file failures remain visible to the operator.

**Reread:** d26 — Wireshark wiki "Libpcap File Format", tcpdump man page (`-r` and filters), Wireshark User's Guide "Capturing"; d22 — Beej's Guide, datagram sockets, and `socket` docs (`SOCK_DGRAM`).


### E6 — Count failed checks from the bench log (easy, ~9 min)

**Goal:** Give the operator a count of failed readings for each affected channel. This combines d04's CSV reading with d12's grouped failure reports in a new limits-checking task.

**Signature:** `def limit_failures(path: Path) -> dict[str, int]`

**CSV** (comma-separated values) is a text table with named columns in its first row, the **header**. Open the file as UTF-8 text with `newline=""` and use the supplied `csv` module. Every input has exactly the header `channel,value,low,high`, followed by complete rows and possibly completely empty lines. Preserve channel text exactly, including quoted commas or non-English characters. Skip completely empty lines. No header or field-count validation is needed.

Convert `value`, `low`, and `high` with `float`. A **limit** is an allowed measurement boundary: a reading fails only if it is strictly below `low` or strictly above `high`. Both endpoints pass. All numeric values are finite. Reject `low > high` with `ValueError`, even if the row's reading would otherwise pass. Let invalid numeric text raise `ValueError` and file errors reach the caller; do not skip damaged rows or return partial results.

Return an ordinary dictionary mapping each channel with failures to its number of failed rows. Count repeated rows separately, and omit channels that only pass. Header-only files return `{}`. Dictionary key order does not matter; leave the file unchanged.

**Example:**

```csv
channel,value,low,high
sense_A,3.1,3.2,3.4
sense_B,5.0,4.9,5.1
sense_A,3.5,3.2,3.4
```

returns `{"sense_A": 2}`.

**Watch out:** Use a fresh count for each channel. Splitting text on commas breaks quoted channel names; `csv.DictReader` handles them for you.

Reread: d04

### E7 — Measure through a multiplexer and disconnect (medium, ~9 min)

**Goal:** Read a chassis signal through a **multiplexer**, a switch that connects one selected input to the station's meter, and disconnect when the step ends.

**Signature:** `def sample_mux(channel: int, write: Callable[[str], None], query: Callable[[str], str]) -> float`

A **transport** carries instrument commands and replies. Here you receive its two methods as arguments: `write(command)` sends text with no reply; `query(command)` sends text and returns a reply string. `Callable` describes a function you can call. Tests pass methods of a **fake**, a replacement that records commands and supplies replies without hardware. Do not create a connection.

First reject an integer channel outside 1-8 with `ValueError`, before any calls. For a valid channel:

1. Write exactly `f"ROUT:CLOS (@{channel})"` to connect that input.
2. Query exactly `"READ?"` once and convert the reply with `float`.
3. Write exactly `"ROUT:OPEN:ALL"` once to disconnect all inputs, then return the measurement.

Attempt the disconnect even if selecting, querying, or converting the reply raises an exception. Let that original exception reach the caller. For this exercise the disconnect command always succeeds; handling a second error during cleanup is outside scope. Send no extra commands, spaces, or newline characters. Each new call repeats the full sequence, even on the same channel.

**Example:** With channel 3 and query reply `" 2.750\n"`, calls are write `"ROUT:CLOS (@3)"`, query `"READ?"`, write `"ROUT:OPEN:ALL"`; return `2.75`.

**Watch out:** d18's `try`/`finally` pattern guarantees cleanup when leaving a block. Put validation before that block so an invalid channel sends nothing. A failed measurement must not turn into a plausible zero.

Reread: d17
