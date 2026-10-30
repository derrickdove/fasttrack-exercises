# d23 — SCPI over Ethernet: a raw TCP socket client

**Time:** about 45 minutes · **Read first:** [Python Socket Programming HOWTO](https://docs.python.org/3/howto/sockets.html); [The Linux Command Line, ch. 16: networking (ping, ip, ss, ssh)](https://linuxcommand.org/tlcl.php); [Python socket docs: create_connection and settimeout](https://docs.python.org/3/library/socket.html) · **You edit:** `starter/tcp_instrument.py`

## What you're building

Your test station controls a bench instrument over Ethernet, a network connection between devices. SCPI (Standard Commands for Programmable Instruments) is a text command language used by instruments; here, `OUTP ON` enables an output and `MEAS:VOLT?` asks for voltage. A query is a command that asks for a reply. Build a client that connects, sends commands, and collects complete replies so a test step can use the measurement.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/tcp_instrument.py`. Don't edit `tests/`. E3 improves the methods you wrote in E2; it has no separate method stub.
2. Press **Ctrl+Shift+B → Test: d23** (or run `bash tools/run.sh d23` / `tools\run.ps1 d23`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

TCP (Transmission Control Protocol) delivers an ordered stream of bytes, the numeric units used to transmit data. A socket is the program's connection endpoint; a raw TCP client uses this socket directly. The host identifies the instrument computer, and the port identifies its listening service. Tests use `127.0.0.1` (your own computer) and an automatically assigned port, so no hardware or internet is needed.

A class defines an object's behavior; an instance is one object created from it. A context manager supports `with`, which runs cleanup when the block ends, even after an exception (an error passed to the caller). A timeout bounds how long one blocking socket operation waits; it is not a deadline for the whole query.

UTF-8 is a text encoding: `.encode("utf-8")` turns text into bytes and `.decode("utf-8")` turns bytes back into text. LF (line feed), written `\n`, marks the end of each message here. The `b` prefix makes a bytes literal, such as `b"OK"`. A buffer stores received bytes until a whole reply is available:

```python
pending = b"STAT"
pending += b"US\nNEXT"
line, remaining = pending.split(b"\n", 1)
print(line.decode("utf-8"))  # STATUS
print(remaining)            # b'NEXT'
```

Use `sendall` to send the complete encoded message. `recv` returns up to the requested byte count, so one call might return part of a line, several lines, or `b""` when the peer (the other endpoint) closes. Keep bytes until LF arrives; decode only the complete line because a UTF-8 character may span receives.

## Exercises

### E1 — Connect and release the bench instrument (easy, ~10 min)

**Goal:** Own one socket for the lifetime of a station instrument object.

**Signatures:** `TcpInstrument(host: str, port: int, timeout: float = 2.0)`, `close() -> None`, `__enter__() -> TcpInstrument`, and the supplied `__exit__(...) -> None`.

Connect immediately in `__init__` using `socket.create_connection((host, port), timeout=timeout)`. Use the supplied timeout, in seconds, for subsequent sends and receives too (`settimeout` can set it explicitly). `close()` releases the socket and is safe to call more than once. `__enter__` returns this same instance. `__exit__` always closes and lets any exception continue to the caller.

**Example:** `with TcpInstrument("127.0.0.1", bench_port) as bench:` gives the block a connected `bench`; leaving the block releases it. `bench_port` must be the port where an instrument is actually listening.

**Watch out:** Creating the object already connects; entering `with` should not connect again. Let connection errors propagate. Later tests depend on E1, so complete it first.

**Reread:** Socket Programming HOWTO, “Creating a Socket” and “Disconnecting”; socket docs, `create_connection` and `socket.settimeout`. In The Linux Command Line ch. 16, revisit `ping` (reachability), `ip` (interface addresses), `ss` (socket status), and `ssh` (a secure remote shell). These are diagnostic tools; no shell commands are required by this set.

### E2 — Send a command and collect a complete reply (medium, ~15 min)

**Goal:** Let a station configure the instrument and read a measurement.

**Signatures:** `write(cmd: str) -> None`, `query(cmd: str) -> str`.

`write` sends `(cmd + "\n")` encoded as UTF-8, without waiting for a reply. `query` sends its command in the same way, then reads exactly one LF-terminated reply. Return the decoded text with only the final LF removed. Preserve leading/trailing spaces; an empty reply is `""`. Keep any bytes after the first LF for the next reply, including across method calls. You may add a private helper method (an internal method, conventionally named with a leading underscore) for reading one reply.

All supplied commands are strings without CR (`\r`, carriage return) or LF. Replies use LF, not CRLF. No command validation or SCPI parsing is required. If `recv` returns `b""` before a full reply is available, raise `ConnectionError`; never return an incomplete measurement.

**Example:** `bench.write("OUTP ON")` sends `b"OUTP ON\n"`. If `bench.query("MEAS:VOLT?")` receives `b" 28."` then `b"0 \n"`, return `" 28.0 "`.

**Watch out:** `strip()` would remove meaningful spaces. Do not assume one `recv` equals one reply, or discard later reply bytes. Add timeout messages in E3.

**Reread:** Socket Programming HOWTO, “Using a Socket”, especially partial sends/receives and delimiting messages (marking message boundaries).

### E3 — Tell the operator which command timed out (easy, ~8 min)

**Goal:** Make a silent instrument produce a useful test-step error.

**Signatures:** Improve `write` and `query`; there is no new public method.

If sending a command or waiting for its complete reply times out, raise the built-in `TimeoutError` with the exact command text somewhere in its message. This includes a reply that starts arriving but never reaches LF. Keep E1's configured timeout. A connection attempt has no command yet, so its errors need no command text.

**Example:** A silent `bench.query("MEAS:CURR?")` raises `TimeoutError("Timed out reading reply to 'MEAS:CURR?'")`. Other wording is fine if it includes `MEAS:CURR?`.

**Watch out:** Catch a socket timeout, not every exception. In current Python, `socket.timeout` is an alias of `TimeoutError`. After a timeout or broken connection, the caller should close the client; recovering that connection is outside this set. You are not asked to retry or turn an error into a measurement value.

**Reread:** socket docs, `socket.settimeout` and “Notes on socket timeouts”; Socket Programming HOWTO, “Using a Socket”.

### E4 — Pipeline a station measurement batch (medium, ~12 min)

**Goal:** Ask for several measurements without waiting between commands.

**Signature:** `query_many(cmds: list[str]) -> list[str]`.

Pipelining means sending every command before starting to read any replies. Use E2's command encoding and reply rules. Return one reply for each command, in the same order, preserving duplicate commands and leaving the input list unchanged. `[]` returns `[]` without sending or reading. Later `query` or `query_many` calls must still work on the same connection.

Carry E3's error handling forward: a send timeout names the command being sent; a read timeout names the command whose reply is currently awaited. Raise the error rather than return a partial list.

**Example:** `bench.query_many(["MEAS:VOLT?", "MEAS:CURR?"])` sends both lines first. Receiving `b"28.0\n0.25\n"` returns `["28.0", "0.25"]`.

**Watch out:** Calling `query` once per command is sequential, so it fails when an instrument waits for the entire batch before replying. Reuse a reply-reading helper, and preserve extra bytes when a receive contains several replies.

**Reread:** Socket Programming HOWTO, “Using a Socket”, especially its warning that a receive can include the start of the following message.

