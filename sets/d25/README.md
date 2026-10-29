# d25 — TCP command channel: framing and partial reads

**Time:** about 45 minutes · **Read first:** Python [Socket Programming HOWTO — Using a Socket and message framing](https://docs.python.org/3/howto/sockets.html#using-a-socket), the [`socket.sendall` reference](https://docs.python.org/3/library/socket.html#socket.socket.sendall), and Missing Semester [Metaprogramming — build systems, dependencies, and continuous integration](https://missing.csail.mit.edu/2020/metaprogramming/) · **You edit:** `starter/framing.py`

## What you're building

A chassis test station sends commands to an instrument over TCP (Transmission Control Protocol), an ordered stream of bytes delivered over a network connection. The instrument must distinguish one command from the next even when a read returns only part of a command, or several replies arrive together. You will encode messages, collect partial reads, and complete a command/reply exchange.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/framing.py`. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: d25** (or run `bash tools/run.sh d25` / `tools\run.ps1 d25` from the repository root). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **byte** is an integer from 0 to 255; a `bytes` object is an immutable sequence of bytes, written for example as `b"CH1?"`.
A **payload** is the message's content; a **frame** adds boundary information to that content.
A **header** contains information about a message; a **length prefix** is a header before the payload that states its size; **big-endian** puts the most significant byte first.
A **buffer** holds bytes until enough have arrived to process them; `bytearray` is a mutable byte sequence.
A **socket** is the connection endpoint; its **peer** is the instrument at the other end.
A **partial read** returns fewer bytes than requested; `recv(n)` returns at most `n` bytes, and `b""` means **EOF** (end of stream: the peer closed its sending side).
`sendall(data)` keeps sending until all data has been sent, or raises an error; `send(data)` may send only part.
A **timeout** limits how long a socket operation may wait; the caller configures it, and your functions let socket errors propagate.

For example, these are integer/byte conversions, using a two-byte field unrelated to our four-byte frame header:

```python
field = (513).to_bytes(2, "big")
assert field == b"\x02\x01"
assert int.from_bytes(field, "big") == 513
pending = bytearray(b"CH")
pending.extend(b"1?")
```

A **dependency** is a prerequisite: E4 uses E1 and E3, so finish those first. **Continuous integration (CI)** runs checks automatically after code changes; rerunning this set locally is the same habit on your own machine. The supplied tests use only a local connection and need no instrument or internet.

## Exercises

### E1 — Encode an instrument command (easy, ~7 min)

**Goal:** Package a command as a four-byte unsigned length (no negative values), followed immediately by the unchanged payload. The length counts payload bytes only. There is no text decoding, newline, or terminator (extra end marker).

**Signature:** `def frame(payload: bytes) -> bytes`

**Example:** `frame(b"ID?")` → `b"\x00\x00\x00\x03ID?"`; `frame(b"")` → four zero bytes.

**Watch out:** Binary content (raw bytes rather than decoded text), including zero bytes, is valid. Inputs fit in the four-byte length field (at most `2**32 - 1` bytes). E1 does not impose E2's incoming-message limit.

**Reread:** Socket HOWTO, Using a Socket: fixed-length, delimited, and length-prefixed messages.

### E2 — Collect instrument replies across reads (medium, ~16 min)

**Goal:** Implement `FrameReader()` and `feed`. Each instance starts empty. Each call appends its **chunk** (bytes supplied in one call) to the saved bytes and returns a `list[bytes]` of every complete payload now available, in order, without headers. Save an incomplete header or payload for the next call; never return a payload twice. Different reader instances must keep separate buffers.

**Signatures:** `def __init__(self) -> None`; `def feed(self, chunk: bytes) -> list[bytes]`

**Example:** For a fresh reader, `feed(b"\x00\x00")` → `[]`, then `feed(b"\x00\x02OK\x00\x00\x00\x00")` → `[b"OK", b""]`.

**Watch out:** A chunk may contain zero, one, or many frames. Every split position must work, including inside the four-byte header. `feed(b"")` adds nothing; it does not signal EOF. Here **1 MB means exactly 1,000,000 payload bytes**. Accept that size; raise `ValueError` as soon as an available complete header declares more, even if its payload has not arrived. After that error, discard the reader; recovery behavior is not specified.

**Reread:** Socket HOWTO, Using a Socket: the length itself may need multiple reads, and a read may include the next message's start.

### E3 — Read exactly the requested bytes (easy–medium, ~9 min)

**Goal:** Read exactly `n` bytes from an already connected socket. Keep calling `recv` with the number still missing. Return `bytes`; do not consume bytes belonging to the next message.

**Signature:** `def recv_exact(sock: socket.socket, n: int) -> bytes`

**Example:** If successive reads supply `b"O"` and `b"K"`, `recv_exact(sock, 2)` → `b"OK"`.

**Watch out:** `n == 0` returns `b""` without reading. Negative `n` raises `ValueError` without reading. If `recv` returns `b""` before you have `n` bytes, raise `ConnectionError`, including when no bytes arrived. Do not close the socket or change its timeout. Other socket errors propagate to the caller.

**Reread:** Socket HOWTO, Using a Socket: `recv` can return fewer bytes than expected, and zero bytes means the connection is broken.

### E4 — Exchange one test-station command (medium, ~13 min)

**Goal:** On an already connected socket, call `sendall` with the E1 frame, then read one reply's four-byte header and its payload using E3. Return the payload alone. There is one outstanding command at a time (send it, then wait for its reply).

**Signature:** `def request(sock: socket.socket, payload: bytes) -> bytes`

**Example:** Sending `b"STATUS?"` and receiving `b"\x00\x00\x00\x02OK"` returns `b"OK"`.

**Watch out:** Empty commands and empty replies are valid. Apply E2's 1,000,000-byte limit to the reply; reject an oversized length immediately with `ValueError`. An incomplete reply header or payload raises `ConnectionError`. Read only this reply, leaving any following bytes for later; leave the socket open and its timeout unchanged. Socket errors propagate. Tests include a **threaded server** (a local instrument simulator running concurrently in another thread) that calls `sendall` once per byte. TCP may still combine those writes; separate scripted tests guarantee partial reads.

**Reread:** Socket HOWTO, Using a Socket, and `socket.sendall`; Missing Semester Metaprogramming, build dependencies and continuous integration: rerun all four exercises after combining E1 and E3 here.
