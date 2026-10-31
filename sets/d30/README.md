# d30 — Packet captures: reading a pcap file

**Time:** about 45 minutes · **Read first:** [The libpcap file format](https://wiki.wireshark.org/Development/LibpcapFileFormat) and [The Linux Command Line](https://linuxcommand.org/tlcl.php), ch. 15, Storage Media (mounts overview) · **You edit:** `starter/pcap.py`

Supplemental readings from the set specification: [tcpdump manual](https://www.tcpdump.org/manpages/tcpdump.1.html), `-r` and filter expressions; [Wireshark User's Guide, Capturing](https://www.wireshark.org/docs/wsug_html_chunked/ChapterCapturing.html), capture concepts. These explain how operators collect or inspect files; no capture tool installation is required here.

## What you're building

A chassis test station saves network traffic when an instrument drops readings. You will read that saved capture, select its telemetry (measurements sent by a device), and report which packets passed an integrity check. A capture is a saved copy of network traffic; this set reads files offline, without opening a network connection.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/pcap.py`. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: d30** (or run `bash tools/run.sh d30` / `tools\run.ps1 d30`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report all pass / partial / stuck in the tracker.

`bytes` holds raw byte values (each 0..255). An **offset** counts bytes from zero. A **slice** selects a range, excluding its end. A **bit** is a binary digit, 0 or 1; a byte contains eight bits. An **unsigned** integer cannot be negative. Hexadecimal (base 16) notation uses digits 0..9 and a..f; Python writes it with a `0x` prefix. **Byte order** says which end of a multi-byte integer holds the largest place value: big-endian puts it first; little-endian puts it last. `struct.unpack` decodes fixed-width fields; `>` selects big-endian, `<` little-endian, `H` a 2-byte unsigned integer, `I` a 4-byte unsigned integer, `Q` an 8-byte unsigned integer, `i` a 4-byte signed integer, and `f` a 4-byte float.

```python
import struct
raw = bytes.fromhex("00 2a 00 03")
step, attempts = struct.unpack(">HH", raw)
print(step, attempts)  # 42 3
```

A **binary file** opened with `open(path, "rb")` returns bytes from `f.read(n)` (at most n bytes). `with open(...) as f:` closes it automatically. A **dictionary** maps names to values. A **tuple** groups values in a fixed order, such as `(time, frame)`; a **list** collects items in order. An **iterator** produces items one at a time; `yield item` makes a function produce such an iterator. `list(iterator)` collects its items. `Path` is a filesystem path from `pathlib`; `str | Path` means either type is accepted. All file paths below can be absolute or relative to the current working directory; from this set's directory, `Path("data/telemetry.pcap")` selects the supplied file. No mount (attaching a storage device to a directory) is needed.

The four functions build on one another. Use only Python's standard library, particularly `struct`, `pathlib`, and `zlib`. File-opening errors propagate normally. Error messages are your choice. File-format errors raise `ValueError`; malformed network or telemetry packets are skipped as specified below. Do not catch `NotImplementedError` from an earlier exercise.

## Exercises

### E1 — Identify the station's capture format (easy, ~8 min)

**Goal:** Decode the global header, the 24-byte block describing the whole pcap (packet capture) file.

**Signature:** `def read_global_header(f: BinaryIO) -> dict[str, int | str]`

`BinaryIO` means an already-open binary file, including an in-memory `io.BytesIO`. Read exactly 24 bytes from its current position; leave it open and positioned immediately after those bytes. The first four bytes are a **magic value**, a fixed identifier: `d4 c3 b2 a1` means little-endian (`"<"`), and `a1 b2 c3 d4` means big-endian (`">"`). A microsecond is one millionth of a second; a nanosecond is one billionth. Only the classic microsecond format is supported; reject other magic values, including nanosecond pcap and pcapng (another capture format).

Decode the remaining 20 bytes using that order and format `HHiiII`:

| Offset | Size | Field |
| --- | --- | --- |
| 4 | 2 | version_major, must be 2 |
| 6 | 2 | version_minor, must be 4 |
| 8 | 4 | reserved time-zone value, ignore |
| 12 | 4 | reserved accuracy value, ignore |
| 16 | 4 | snaplen, must be positive |
| 20 | 4 | linktype |

**Snaplen** is the maximum stored bytes per frame; a **frame** is one message on the local network. A **layer** is one protocol wrapped around the next; a protocol is an agreed message format. **Linktype** identifies the outermost network format; 1 means Ethernet, the wired-network format used in E3. Return exactly the keys below. E1 accepts any linktype. Raise `ValueError` for fewer than 24 bytes, unknown magic, a version other than 2.4, or zero snaplen.

**Example:** The supplied file returns `{"byteorder": "<", "version_major": 2, "version_minor": 4, "snaplen": 65535, "linktype": 1}`.

**Watch out:** Byte order applies to the file headers, not to bytes inside a frame. **Reread:** Libpcap File Format, Global Header and its field descriptions.

### E2 — Walk the saved station traffic (easy–medium, ~10 min)

**Goal:** Stream stored frames without loading the whole file first.

**Signature:** `def iter_records(path: str | Path) -> Iterator[tuple[float, bytes]]`

Open the file in binary mode, use E1, then read records in file order. A **record** is a 16-byte header followed by its stored frame bytes. Its header has four unsigned 4-byte integers (`IIII`) in the global header's byte order: seconds since the Unix epoch (1970-01-01 UTC), microseconds within that second, captured length, and original length. The original length may exceed the captured length when capture was shortened; only read the captured bytes. A microsecond is one millionth of a second.

Yield `(seconds + microseconds / 1_000_000, frame_bytes)` for every record, including empty frames. Stop at **EOF** (end of file) only when the next header read returns zero bytes. Close the file when iteration finishes. Raise `ValueError` for a partial record header, partial frame, microseconds >= 1,000,000, captured length greater than snaplen, or captured length greater than original length. A global-header-only file yields nothing. E1 errors propagate; E2 accepts any linktype. Errors may occur when consuming the iterator rather than when creating it.

**Example:** A record with seconds 10, microseconds 250000, and frame `b"abc"` yields `(10.25, b"abc")`. The supplied capture has seven records.

**Watch out:** A saved capture on mounted storage is still an ordinary file; its path is independent of the interface that originally captured it. **Reread:** Libpcap File Format, Record (Packet) Header and Packet Data; The Linux Command Line ch. 15, Mounting and Unmounting Storage Devices (overview).

### E3 — Extract one instrument's UDP messages (medium, ~17 min)

**Goal:** Select the data addressed to a test-station port.

**Signature:** `def udp_payloads(path: str | Path, port: int) -> list[bytes]`

Inputs for E3/E4 always have linktype 1. A **port** is a numbered application endpoint; reject a port outside 0..65535 with `ValueError`. A **payload** is the data inside a message, after its header. Use E2 and preserve file order and duplicates. For each frame, follow these layers; all multi-byte integers inside frames are big-endian, even in little-endian pcap files:

1. **Ethernet** has a 14-byte header. Bytes 12:14 are the **EtherType**, identifying the next layer. Only `0x0800` (IPv4) is supported; skip other types, including VLAN-tagged frames (frames with an added network-separation tag).
2. **IPv4** (Internet Protocol version 4) starts at frame offset 14. The high four bits of its first byte must equal 4. The low four bits are **IHL**, Internet Header Length, in 4-byte words: `(first_byte & 15) * 4`. IHL must be at least 20 bytes and fit in the stored data. Larger headers contain **options**, extra header fields; skip over them. IP-relative bytes 2:4 give total IP length, including the IP header. It must be at least IHL + 8 and at most the stored IP bytes. IP-relative byte 9 must be 17 for UDP. IP-relative bytes 6:8 hold fragmentation flags and an offset: skip if `(value & 0x3fff) != 0`. A **fragment** is one piece of a split message; this exercise does not join pieces. The `0x4000` don't-fragment flag is allowed.
3. **UDP** (User Datagram Protocol) starts immediately after the IP header. Its 8-byte header has source port (bytes 0:2), destination port (2:4), UDP length (4:6), and checksum (6:8). UDP length includes its header; it must be at least 8 and at most `IP total length - IHL`. Select by **destination**, not source. Return bytes from UDP offset 8 up to UDP length. Empty payloads are valid.

Skip frames that fail any structural rule above, including truncated headers or data. Ignore Ethernet padding (extra bytes after the IP message) and IP bytes after the declared UDP length. Do not validate IP or UDP checksums (integrity fields). Propagate E2's file errors.

**Example:** `udp_payloads(path, 5005)` returns only payloads addressed to port 5005. In the supplied capture it returns four payloads, including one with a bad telemetry CRC (cyclic redundancy check, a value used to detect corruption).

**Watch out:** Never assume every IP header is exactly 20 bytes. Useful operations: `int.from_bytes(raw, "big")`, `value >> 4` (shift right four bits), and `value & mask` (retain only selected bits). **Reread:** Libpcap File Format, Packet Data (the captured bytes start after each record header); supplemental tcpdump manual, `-r` and `udp dst port` filters.

### E4 — Summarize trustworthy telemetry (medium, ~10 min)

**Goal:** Give the operator `(sequence, channel_count)` for every valid telemetry packet returned by E3.

**Signature:** `def telemetry_from_capture(path: str | Path, port: int) -> list[tuple[int, int]]`

This uses the capstone telemetry wire format, repeated here so this set is independent. A **sequence** number labels a packet; a **channel** identifies one measured input. A **CRC**, cyclic redundancy check, detects corruption by comparing a calculated value with the transmitted value. All fields are big-endian:

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 2 | sync marker, fixed value `0xEB90` |
| 2 | 2 | unsigned sequence number |
| 4 | 8 | unsigned device timestamp in microseconds (ignore its value) |
| 12 | 1 | channel count, 0..255 |
| 13 | count × 5 | entries: 1-byte channel ID, then 4-byte float reading |
| 13 + count × 5 | 4 | unsigned CRC |

Require exactly `17 + 5 * count` bytes, correct sync, unique channel IDs within each packet, and `zlib.crc32(payload[:-4]) == int.from_bytes(payload[-4:], "big")`. Skip anything failing these rules, including short payloads and bad CRCs. Float values need not be decoded or checked; channel IDs need not be sorted. Zero-channel packets are valid. Keep capture order and duplicates; do not sort sequences or infer missing ones. Device timestamps differ from the capture timestamps in E2. E3 errors propagate.

**Example:** For the supplied file and port 5005, return `[(40, 2), (42, 0), (43, 1)]`.

**Watch out:** Check length before indexing fields, then check CRC before trusting the packet. **Reread:** Libpcap File Format, Packet Data (application bytes must be interpreted separately); supplemental Wireshark Capturing chapter, capture concepts. The telemetry layout above is the complete application-specific contract.

## Terminal drill (WSL2 Ubuntu, ~10 min)

This drill is ungraded; its minutes come from the day's readings. Use two Ubuntu terminals in the repo root, with the Linux `.venv` already created by the test runner and `tcpdump` installed. `tcpdump` captures or displays network packets. **Loopback** (`lo`) sends traffic back to this computer; `127.0.0.1` is its IPv4 address.

In terminal A, start a capture and wait until it says it is listening:

```bash
sudo tcpdump -i lo -nn -s 0 -c 1 -w /tmp/fasttrack-lo.pcap 'udp dst port 5005'
```

`sudo` runs the capture with administrator privileges. `-i lo` selects loopback; `-nn` keeps addresses and ports numeric; `-s 0` stores full packets; `-c 1` stops after one matching packet; `-w` saves it to a file. The quoted filter selects UDP packets with destination port 5005. `/tmp` holds temporary files.

In terminal B, send one **datagram** (one UDP message):

```bash
.venv/bin/python -c 'import socket; socket.socket(socket.AF_INET,socket.SOCK_DGRAM).sendto(b"probe", ("127.0.0.1", 5005))'
```

`-c` runs the following Python code; `AF_INET` selects IPv4 and `SOCK_DGRAM` selects UDP. No receiver is needed to capture this outgoing probe. After terminal A exits, read the saved packet there, then inspect the supplied fixture (the fixed sample file used by this set):

```bash
tcpdump -nn -r /tmp/fasttrack-lo.pcap
tcpdump -nn -r sets/d30/data/telemetry.pcap 'udp dst port 5005'
```

`-r` reads a saved capture. Relate the fixture's source and destination addresses to E3's IPv4 header, and its ports and UDP length to E3's 8-byte UDP header. Its first matching packet goes from `192.0.2.10.40000` to `192.0.2.20.5005` with 27 payload bytes: E4's `17 + 5 * 2` bytes for two channels. The displayed addresses and length describe network headers; E4 separately checks the telemetry bytes and CRC.

Keep `/tmp/fasttrack-lo.pcap` for inspection with `tcpdump`, rather than substituting it for the fixture. Loopback has no physical Ethernet framing (the outer header used on a wired network); capture software may supply a synthetic Ethernet header or another linktype. E3 assumes linktype 1 and Ethernet offsets, so it cannot interpret other linktypes. Even if a synthetic Ethernet header lets E3 extract the probe, `b"probe"` is not valid telemetry: it lacks E4's sync marker, fields and CRC. E4 will not accept it as a telemetry packet.
