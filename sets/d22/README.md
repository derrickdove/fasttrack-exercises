# d22 — UDP basics: send and receive datagrams

**Time:** about 53 minutes · **Read first:** [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/html/split/), sockets, TCP vs UDP, and datagram sockets; [Wireshark User's Guide](https://www.wireshark.org/docs/wsug_html_chunked/), capturing and filtering concepts. Also consult Python's [Socket Programming HOWTO](https://docs.python.org/3/howto/sockets.html) and [`socket` docs, SOCK_DGRAM](https://docs.python.org/3/library/socket.html#socket.SOCK_DGRAM). · **You edit:** `starter/udp.py`

## What you're building

A chassis test station collects **telemetry**, measurements sent by an instrument while it runs. You will open a local receiver, send separate messages, collect a bounded batch, and answer an instrument's connection check. These helpers use UDP (User Datagram Protocol), which sends individual messages without first establishing a connection.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/udp.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d22** (or run `bash tools/run.sh d22` / `tools\run.ps1 d22`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **socket** is an operating-system handle for sending or receiving network data. An **IP address** identifies a network interface; `127.0.0.1` is **loopback**, an address that stays on your own computer. A **port** is a number identifying a socket's destination on that computer. An **address tuple** is a fixed pair `(host, port)`, such as `("127.0.0.1", 42000)`; the example port is illustrative, and tests always ask the operating system to choose a free port with `0`.

A **datagram** (called a **packet** here) is one complete UDP message. Unlike TCP (Transmission Control Protocol), which provides an ordered stream of bytes, UDP preserves message boundaries but does not guarantee delivery, order, or uniqueness. Local tests queue small messages; production telemetry needs additional loss handling. A **payload** is the message's data; Python's `bytes` type stores raw byte values, and `b"READY"` is a bytes literal. An empty payload `b""` is a valid UDP message, not a disconnected sender.

`socket.AF_INET` selects IPv4 (Internet Protocol version 4), the address format used by `127.0.0.1`; `socket.SOCK_DGRAM` selects UDP. `bind(address)` assigns a socket its local address, and `getsockname()` returns the actual address, including the port chosen for `0`. `sendto(data, address)` sends one datagram. `recvfrom(buffer_size)` returns `(payload, sender_address)`; its buffer size is the maximum number of bytes it can return, so use `65535` throughout this set to avoid cutting off valid IPv4 UDP messages.

A **timeout** is a limit, in seconds, on how long a socket operation may wait. `settimeout(seconds)` sets it, `gettimeout()` reads it, and `socket.timeout` is the exception raised when it expires. An **idle timeout** measures the wait for the next message: each successful receive starts a fresh wait. `OSError` reports other operating-system errors; **propagate** means let an exception reach the caller instead of hiding it. A `with` statement closes a socket when the block ends; `try`/`finally` runs cleanup even if an exception occurs. The code that owns a socket is responsible for closing it.

ASCII is an encoding (a mapping between bytes and characters) for basic English letters, digits, and punctuation. Here is a separate operator display example: unpack a received pair and inspect its bytes. This does not open or send anything.

```python
packet = (b"chassis=4", ("127.0.0.1", 42000))
payload, sender = packet
print(payload.decode("ascii"))  # chassis=4; decode converts bytes to text
print(sender[1])                # 42000; index 1 selects the port
```

All addresses in this set use IPv4 loopback. Inputs have the stated types; no extra input validation is required. No instrument, internet connection, or Wireshark installation is needed. Wireshark is a tool for capturing network traffic: a **capture filter** selects traffic to record, while a **display filter** selects which recorded packets to show. For example, `udp` shows UDP packets as a display filter. On a real station, capturing loopback traffic lets you inspect the addresses and individual messages these helpers exchange.

## Exercises

### E1 — Open the telemetry receiver (easy, ~10 min)

**Goal:** Create a fresh IPv4 UDP socket, bind it to `(host, port)`, set its timeout, and return the open socket. The caller owns it and will close it. If setup fails, close the new socket and propagate the error.

**Signature:** `def make_receiver(host: str = "127.0.0.1", port: int = 0, timeout: float = 0.5) -> socket.socket`

**Example:** `receiver = make_receiver()` gives an open socket with `receiver.getsockname()[0] == "127.0.0.1"`, a nonzero assigned port, and `receiver.gettimeout() == 0.5`.

**Watch out:** Bind before returning. Port `0` asks the operating system for an available port; it is not the destination port for a sender. Tests also pass a different positive timeout with the same loopback host and port `0`.

**Reread:** Beej, the `socket()` and `bind()` sections and TCP vs UDP discussion; Wireshark, “Capturing Live Network Data,” choosing an interface (look for loopback). Python's HOWTO, “Creating a Socket,” is a useful API companion.

### E2 — Send one instrument message (easy, ~8 min)

**Goal:** Open a temporary IPv4 UDP socket, give it a `0.5` second timeout, send `data` to `addr` in exactly one `sendto` call, and close the temporary socket even if sending fails. Return `None`; propagate send errors. There is no reply to wait for.

**Signature:** `def send_datagram(data: bytes, addr: tuple[str, int]) -> None`

**Example:** `send_datagram(b"current=2.4", receiver.getsockname())` queues one unchanged message for that receiver.

**Watch out:** Preserve bytes exactly, including `b""` and byte values that are not text. Don't encode, append a newline, split, or combine messages. Let the operating system pick the temporary sender's local port. An excessively large payload may raise `OSError`; do not suppress it.

**Reread:** Beej, `sendto()` and “Datagram Sockets”; Wireshark, “Filtering while capturing,” the UDP capture-filter concept. Python's `socket` docs describe `SOCK_DGRAM` and `sendto()`.

### E3 — Collect a telemetry batch (medium, ~17 min)

**Goal:** Read from an already-bound UDP socket until you collect `max_packets` messages or one receive waits `idle_timeout` seconds without a message. Return a list of payloads in the order received. Each successful receive gets a fresh full idle timeout, rather than sharing one deadline for the whole batch.

**Signature:** `def receive_all(sock: socket.socket, max_packets: int, idle_timeout: float) -> list[bytes]`

**Example:** If the receiver has `b"V=24"` and `b"I=2"` queued, `receive_all(receiver, 5, 0.05)` returns `[b"V=24", b"I=2"]` after the next receive times out.

**Watch out:** `max_packets` is a nonnegative integer and `idle_timeout` is positive. For a zero maximum, return `[]` immediately without reading or changing the socket. Otherwise temporarily use the idle timeout, then restore the original timeout on every exit, including errors. A timeout returns the messages collected so far (possibly `[]`); other `OSError` exceptions propagate. Don't close the caller's socket. Count `b""` as a message, discard sender addresses, and leave excess datagrams queued when you reach the maximum. Use `recvfrom(65535)`.

**Reread:** Beej, `recvfrom()` and datagram message boundaries; Wireshark, “Filtering Packets While Viewing,” using `udp` to focus on these messages. Python's `socket` docs cover `settimeout()` and `socket.timeout`.

### E4 — Answer the instrument connection check (medium, ~10 min)

**Goal:** Receive exactly one datagram on the supplied bound socket, reply to that datagram's sender using the same socket, and return the sender's `(host, port)` tuple. Reply with `payload.upper()`: `bytes.upper()` changes ASCII lowercase letters to uppercase and leaves other byte values unchanged.

**Signature:** `def echo_once(sock: socket.socket) -> tuple[str, int]`

**Example:** An instrument sends `b"ready?"`; it receives `b"READY?"`, and your function returns that instrument's address.

**Watch out:** An **echo** is a reply containing the received data (uppercased here). Use `recvfrom(65535)` and one `sendto` call. Preserve an empty message as an empty reply. Leave additional messages queued. The caller supplies a positive timeout; keep that timeout unchanged, leave the socket open, and propagate receive/send errors, including `socket.timeout`. Don't use E2: the reply must come from this receiver's address.

**Reread:** Beej, the sender/receiver example in “Datagram Sockets” and the address returned by `recvfrom()`; Wireshark, the packet-details view, UDP source and destination ports (the sender and receiver port numbers).

### E5 — TCP or UDP? (QUIZ, easy, ~8 min)

**Goal:** Choose a transport protocol (the rules for moving data between programs) for each test-station situation. Return a dictionary mapping exactly the question ids `"Q1"`, `"Q2"`, `"Q3"`, and `"Q4"` to your chosen uppercase option letters (`"A"`, `"B"`, `"C"`, or `"D"`). Each question has one correct option; return letters, not option text.

**Signature:** `def transport_answers() -> dict[str, str]`

**Example:** `sorted(transport_answers())` → `['Q1', 'Q2', 'Q3', 'Q4']`. Here `sorted` lists the dictionary's keys in order; the values are your four answer letters.

**Watch out:** This is a concept check: return answers without opening sockets. SCPI (Standard Commands for Programmable Instruments) is a text command language used by instruments. A **sequence number** is an increasing number attached to each sent sample so a receiver can spot gaps or arrivals out of order. **Message boundaries** mark where one application message ends and the next begins; a **byte stream** is a continuous sequence of bytes. Reliable transport alone does not prove a power supply executed a command: the station must also check the instrument's reply or state and handle connection errors.

**Q1.** A sensor sends a high-rate telemetry stream; occasional missing samples are acceptable, and a late sample is useless because a newer one replaces it. Which transport best matches this requirement?

- A. TCP, because it drops old bytes instead of retrying delivery.
- B. UDP, because the station can use fresh samples without waiting for lost samples to be resent.
- C. TCP, because each send becomes exactly one received message.
- D. UDP, because it guarantees that every sample arrives before its deadline.

<details>
<summary>Why it matters on the job — Q1</summary>

A live station display needs a transport choice that matches how quickly measurements become stale.

</details>

**Q2.** A bench power supply accepts SCPI over either TCP or UDP, and silently losing a command is unacceptable. Which transport should the driver choose before adding instrument reply checks and error handling?

- A. UDP, because a successful send proves the instrument received the command.
- B. UDP, because commands are short enough to guarantee delivery.
- C. TCP, because it provides reliable, ordered byte delivery while the connection works.
- D. Either, because both provide the same delivery guarantees on a local network.

<details>
<summary>Why it matters on the job — Q2</summary>

A missing power-supply command can leave the next test step using the wrong instrument state.

</details>

**Q3.** A UDP telemetry receiver must detect missing samples and samples that arrive out of order. Which guarantees are absent, and what must the application add?

- A. UDP guarantees neither delivery nor ordering; include sequence numbers in sent samples and track them at the receiver to detect gaps and older arrivals.
- B. UDP guarantees delivery but not ordering; the receiver only needs to sort every batch by arrival time.
- C. UDP guarantees ordering but not delivery; the receiver only needs a longer timeout to recover every missing sample.
- D. UDP guarantees both; sequence numbers are only needed to convert bytes to text.

<details>
<summary>Why it matters on the job — Q3</summary>

The operator needs to distinguish a steady measurement from a display that has missed updates.

</details>

**Q4.** An instrument sends two measurement messages in two sends, using either TCP or UDP, and the receiver's UDP buffer is large enough for either message. What does preserving message boundaries mean here?

- A. TCP and UDP both ensure that each receive returns exactly one complete sent message.
- B. TCP preserves each sent message, while UDP may combine both datagrams into one received message.
- C. Neither preserves messages; both require a newline to tell the receiver when a network message ends.
- D. TCP is a byte stream, so receives can split or combine sent messages; UDP keeps each datagram separate.

<details>
<summary>Why it matters on the job — Q4</summary>

A driver must know when it has a complete measurement before trying to interpret its contents.

</details>

**Reread:** Beej's Guide, “Two Types of Internet Sockets” for stream sockets, datagrams, reliability, and packet numbering; “Son of Data Encapsulation” for handling message lengths over a stream. Revisit the datagram `sendto()` / `recvfrom()` examples from this day's reading.
