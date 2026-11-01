# d23 — SCPI over Ethernet: a raw TCP socket client

**Time:** about 60 minutes · **Read first:** [Python Socket Programming HOWTO](https://docs.python.org/3/howto/sockets.html); [The Linux Command Line, ch. 16: networking (ping, ip, ss, ssh)](https://linuxcommand.org/tlcl.php); [Python socket docs: create_connection and settimeout](https://docs.python.org/3/library/socket.html) · **You edit:** `starter/tcp_instrument.py` and `starter/network_diagnosis.py`

## What you're building

Your test station controls a bench instrument over Ethernet, a network connection between devices. SCPI (Standard Commands for Programmable Instruments) is a text command language used by instruments; here, `OUTP ON` enables an output and `MEAS:VOLT?` asks for voltage. A query is a command that asks for a reply. Build a client that connects, sends commands, and collects complete replies so a test step can use the measurement.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/tcp_instrument.py`. Don't edit `tests/`. E3 improves the methods you wrote in E2; it has no separate method stub. E5 has its own stub in `starter/network_diagnosis.py`.
2. Press **Ctrl+Shift+B → Test: d23** (or run `bash tools/run.sh d23` / `tools\run.ps1 d23`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
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

## Network evidence primer (for E5)

An **IPv4 address** identifies a network interface (a device's network connection)
using four numbers from 0 to 255, such as `192.168.70.12`. A **prefix** says how
many leading address bits belong to the network (a bit is a binary digit, 0 or 1).
With `/24`, the first three
numbers identify the **subnet**, a group of addresses treated as directly
reachable: `192.168.70.12/24` and `192.168.70.90/24` share a subnet;
`192.168.71.90/24` does not. All bench interfaces here use `/24`.

A **route** tells the computer where to send packets (small units of network
data). A connected route such as `192.168.70.0/24 dev enp1s0` sends directly
through interface `enp1s0`. A **gateway** is a router that forwards packets to
another network. The **default route**, such as
`default via 192.168.70.1 dev enp1s0`, uses that gateway when no more specific
route matches. Two subnets can communicate through a correctly configured
router; different subnets alone do not prove a fault.

These are recorded Ubuntu 24.04 **iproute2** outputs (Linux network tools), not
commands you must run. `$` marks the recorded command; `[station]` and
`[instrument]` identify which computer produced it. `ip -br addr` lists interface
names, link states, and addresses; `UP` means enabled with a working link, while
`UNKNOWN` on `lo` is normal. `lo` is the **loopback** interface for the computer
itself. `::1/128` is its IPv6 loopback address; IPv6 is another address format and
is not used for these connections. `ip route` lists IPv4 routes; `dev` names the
interface, `src` its source address, `proto kernel` a route created from an
interface address, and `scope link` a directly reachable network.

A **service** is a program accepting network requests. `ss -ltn` lists
**listeners**, services waiting for TCP connections, using numeric
addresses and ports. In `0.0.0.0:5025`, port 5025 accepts connections on any local
IPv4 interface. `Local Address:Port` names the listener, `Peer Address:Port`
is the remote endpoint (`*` means any), and `Recv-Q`/`Send-Q` are queue counts
(for a listener, pending connections and the maximum allowed pending count).
The optional `Process` column is empty without process details. SSH (Secure
Shell) provides a remote command prompt; its port 22 listener is separate
from the SCPI service.

For a Python **connection attempt** (before sending any command):

- `ConnectionRefusedError`: the host was reached but nothing is listening on
  that port in these captures. Check both the client's port and the listener.
  A real firewall (a packet-filtering rule) can also actively reject connections.
- `TimeoutError`: packets were dropped or the host did not answer before the
  timeout. This alone cannot identify a bad address, a cable fault, or filtering.
- `OSError: [Errno 101] Network is unreachable`: the station has no usable route
  to the destination in these captures. Changing the timeout cannot add a route.

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

### E4 — Query a station measurement batch in order (medium, ~12 min)

**Goal:** Collect several measurements, completing each query before sending the next.

**Signature:** `query_many(cmds: list[str]) -> list[str]`.

Send the first query and read its complete LF-terminated reply before sending the next query. Repeat for every command, using E2's command encoding and reply rules. Return one reply for each command, in the same order, preserving duplicate commands and leaving the input list unchanged. `[]` returns `[]` without sending or reading. Later `query` or `query_many` calls must still work on the same connection.

Carry E3's error handling forward: a send timeout names the command being sent; a read timeout names the command whose reply is currently awaited. Raise the error rather than return a partial list.

**Example:** `bench.query_many(["MEAS:VOLT?", "MEAS:CURR?"])` sends `b"MEAS:VOLT?\n"`, reads `b"28.0\n"`, then sends `b"MEAS:CURR?\n"` and reads `b"0.25\n"`. It returns `["28.0", "0.25"]`.

**Watch out:** Most instruments expect one query at a time. Pipelining (sending more queries before reading earlier replies) is a device-specific feature; only use it when the instrument explicitly supports it. Calling `query` once per command gives this batch the required order.

**Reread:** Socket Programming HOWTO, “Using a Socket”, especially its warning that a receive can include the start of the following message.

### E5 — Why can't the station reach the instrument? (medium, ~15 min)

**Goal:** Diagnose recorded connection failures before changing a driver.

**Signature:** `def diagnose_network() -> dict[str, dict[str, str]]` in
`starter/network_diagnosis.py`.

A **switch** connects devices on the local network. An **approved** setting is
the station's documented intended configuration, given at the top of each
capture; a **reserved** address is allocated to that station so it can be used
without conflicting with another device. These are proposed fixes, not commands
to run on a real station.

Read every `data/*.txt` capture as evidence. These are invented, independent
station runs with realistic command output, not measurements from your computer.
Each file gives the intended wiring and approved configuration, the client's
connection target, the Python error, and address, route, and listener output from
both computers. Treat the capture's stated conditions as facts. No hardware,
Linux installation, shell execution, network access, or file parser is required:
read the files yourself and return your decisions as a dictionary.

**Contract:** Return one entry for every `.txt` file in `data/`, keyed by the
filename without `.txt` (for example, `case_a`). Each value is a separate
dictionary with exactly two keys, `diagnosis` and `fix`. All values are
case-sensitive strings from the following tables, with no extra whitespace.
Choose the best-supported cause and its next action; do not guess a specific
physical fault from a timeout alone. E5 is independent of E1 through E4.

| `diagnosis` vocabulary | Meaning |
| --- | --- |
| `wrong_subnet` | The station's bench address/prefix disagrees with the approved direct instrument network. |
| `no_route` | The station's local address is correct, but no route reaches the instrument's network. |
| `nothing_listening` | The client uses the approved SCPI port, but the instrument has no listener there. |
| `wrong_port` | The instrument listens on its approved SCPI port, but the client requests another port. |
| `no_response` | Addressing, routing, and the expected listener are consistent; the timeout requires more path/host evidence. |

| `fix` vocabulary | Next action |
| --- | --- |
| `set_station_address` | Set the station bench interface to its approved, reserved IPv4 address/prefix, then reconnect. |
| `add_default_route` | Restore the approved default gateway on the station, then reconnect. |
| `start_scpi_service` | Start the instrument's SCPI service on its approved port, confirm its listener, then reconnect. |
| `use_scpi_port` | Change the client's target port to the approved SCPI listener, then reconnect. |
| `check_path_and_host` | Check host availability, cable/switch connections, and filtering along the path before reconnecting; the capture does not isolate one of them. |

**Example:** `len(diagnose_network())` returns `5`. The files `case_a.txt` through
`case_d.txt` are your first four cases; inspect the data directory for the
additional capture too. The README does not supply any case's diagnosis or fix.

**Watch out:** Compare both ends and the requested port. A default route can
send a mistaken bench address toward another network, producing a timeout
rather than an immediate unreachable error. A listener on port 22 says nothing
about port 5025. The grader checks answer fingerprints (digests computed from
the answer text) and gives rereading hints without printing answer values.

**Reread:** The network evidence primer above; The Linux Command Line ch. 16,
`ip` and `ss`; Python socket docs, connection errors.
