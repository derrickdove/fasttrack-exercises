# d27 — Concurrency for I/O: threads, queues and clean shutdown

**Time:** about 53 minutes · **Read first:** [Python threading docs: Thread and Event](https://docs.python.org/3/library/threading.html), [Python queue docs](https://docs.python.org/3/library/queue.html), [Python glossary: global interpreter lock](https://docs.python.org/3/glossary.html#term-global-interpreter-lock), and [Pro Git 7.1: Revision Selection](https://git-scm.com/book/en/v2/Git-Tools-Revision-Selection) · **You edit:** `starter/workers.py`

## What you're building

A chassis test station must read instruments and receive telemetry (measurements sent by another device) while the operator continues working. Build background readers and a worker pool that finish cleanly when the station stops. All network tests use this computer only; no hardware is needed.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/workers.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d27** (or run `bash tools/run.sh d27` / `tools\run.ps1 d27`). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

**I/O** means input/output, such as waiting for an instrument reply. **Concurrency** means tasks can make progress during one another's waits. A **thread** is a separate flow of execution in the same Python process; `Thread.start()` runs its `run()` method in the background, and `join(timeout=...)` waits for it to finish. `is_alive()` tells you whether it is still running.

An **Event** is a shared signal: one thread calls `set()`, and another checks `is_set()` or uses `wait(timeout)`. A **Queue** safely transfers items between threads in first-in, first-out order. `get(timeout=...)` waits for an item or raises `queue.Empty`; `put_nowait(item)` adds an item without waiting. A **callable** is something you can call like a function. **Busy-waiting** repeatedly checks for work without blocking, wasting processor time.

```python
from queue import Queue
from threading import Event
ready = Event()
readings = Queue()
readings.put_nowait(28.1)
ready.set()
```

A **socket** is a network endpoint. **UDP** sends separate messages called **datagrams**; `recvfrom(size)` returns `(bytes_received, sender_address)`. A **parser** converts bytes into a usable value. A **timeout** bounds how long a blocking call waits. A **worker pool** is a fixed group of threads sharing jobs. A **sentinel** is a special queue item that tells a worker to exit.

For this set, caller-supplied queues are unbounded (no fixed size limit; `Queue()`), and each source/parser/worker call finishes within 0.2 seconds. No forced thread cancellation is needed. `drain` and the background readers do not call `task_done()` (the optional queue task counter is outside this set). Use only the standard library. Never inspect private Queue fields.

## Exercises

### E1 — Background instrument producer (easy, ~8 min)

**Goal:** Subclass `Thread` to collect successive instrument readings. A **subclass** extends an existing class; `super().__init__()` initializes its base class.

**Signatures:** `Producer(source: Callable[[], object], output: Queue[object], stop_event: Event)` and `run() -> None`.

Initialize the base `Thread` and save the arguments; construction does not start it. In `run`, check the event before every source call. Each call takes no arguments and returns one item; preserve items exactly, including `None`, and enqueue them in read order. `StopIteration` means the source is exhausted: return normally. If the event becomes set during a source call, discard that call's result and exit. An already-set event means zero source calls. Other source exceptions are outside this exercise.

**Example:** A source returning `28.1`, `28.2`, then raising `StopIteration` leaves `[28.1, 28.2]` in the output queue after `start()` and `join(timeout=2)`.

**Watch out:** Override `run`, not `start`. Don't name an attribute `_stop`: `Thread` already uses it. The caller owns the event and joins the producer; don't clear the event.

**Reread:** threading docs, “Thread objects” (`__init__`, `run`, `start`, `join`) and “Event objects”; queue docs, `Queue.put_nowait`.

### E2 — Collect a burst of station readings (easy, ~7 min)

**Goal:** Remove readings until the queue has been quiet for one timeout interval.

**Signature:** `drain(q: Queue[T], timeout: float) -> list[T]`. `T` means any item type, preserved in the result.

Call `q.get(timeout=timeout)` for each item, appending it to a list. Return on the first `Empty`. The timeout starts again for each get; it is an idle interval, not a total deadline. A zero timeout removes only immediately available items. Reject a negative timeout with `ValueError` before removing anything. Do not use `empty()`, `qsize()`, or a polling loop to decide when to stop.

**Example:** A queue containing `28.1`, `28.2` gives `drain(q, 0) == [28.1, 28.2]`, and the next call gives `[]`.

**Watch out:** Empty right now does not mean a background producer has finished. A positive timeout lets a later reading arrive while `get` is waiting.

**Reread:** queue docs, `Queue.get`, `Empty`, and the warnings on `empty()` and `qsize()`; threading docs, “Event objects”.

### E3 — Stoppable UDP telemetry listener (medium, ~15 min)

**Goal:** Receive telemetry while the station runs, then release its network resource.

**Signatures:** `Listener(sock: socket, output: Queue[object], parse: Callable[[bytes], object])`, `start() -> None`, `stop() -> None`, and `_receive() -> None` (the internal receiver loop).

The caller supplies a UDP socket already bound to `127.0.0.1` (this computer) and port `0` (let the operating system select an available port). **Binding** assigns a socket its local address. The listener takes ownership: set its receive timeout to **0.2 seconds** in `__init__`, and close it in `stop`. Expose `stop_event: Event` (initially clear) and `thread: Thread | None` (initially `None`). Construction does not start a thread.

`start` launches one thread running `_receive`. Every later `start`, including after stopping, raises `RuntimeError`. In the loop, receive with `recvfrom(65535)`, pass only the received bytes to `parse`, and enqueue the returned object unchanged, including `None`. On `socket.timeout`, check the stop event and keep listening. On a parser `ValueError`, discard that datagram and keep listening. Other parser errors and external socket closure are outside the contract.

`stop` sets the event, joins the receiver with a maximum two-second wait, and closes the socket after the thread exits. If a thread remains alive after that wait, raise `RuntimeError`. Stopping before starting closes the socket and prevents a future start. Repeated stops are harmless. Call `start`/`stop` only from the controlling thread; neither method returns a value.

**Example:** With `parse=lambda packet: float(packet.decode("ascii"))`, receiving `b"28.1"` adds `28.1` to the output queue; receiving `b"bad"` adds nothing.

**Watch out:** `recvfrom` must time out so an idle listener can notice a stop request. Do not wait for another datagram to shut down. You may receive one final item if parsing was already underway when stopped.

**Reread:** threading docs, `Thread.start`, `Thread.join`, `Thread.is_alive`, and “Event objects”; queue docs, `Queue.put_nowait`. Optional API lookup: [socket timeouts](https://docs.python.org/3/library/socket.html#socket.socket.settimeout) and [recvfrom](https://docs.python.org/3/library/socket.html#socket.socket.recvfrom).

### E4 — Parallel station checks with ordered results (medium, ~15 min)

**Goal:** Run independent instrument checks using threads sharing a job queue.

**Signature:** `run_pipeline(items: Iterable[T], workers: int, fn: Callable[[T], R]) -> list[R]`. An **iterable** supplies items one at a time; `R` means the result type may differ from the input type.

`workers` is an integer. Reject values below 1 with `ValueError`, even for empty input, before consuming `items`. Consume the finite iterable once. For empty input return `[]` without calling `fn` or starting workers. Otherwise start `min(workers, number_of_items)` worker threads. Queue indexed jobs (each paired with its zero-based input position) and one exit sentinel per worker. Call `fn` exactly once for every input occurrence, including duplicates and `None`; the workers must actually overlap when there are multiple workers and waiting jobs.

Return results in input order, even when jobs finish in a different order. Catch ordinary `Exception` failures from `fn`, record them, and keep processing all remaining jobs. After every worker has stopped, re-raise the original exception object from the first failure recorded by a worker. Simultaneous failures may be recorded in either order. Use a queue to record failures safely. `KeyboardInterrupt` and other `BaseException` subclasses are outside the contract. Never return or raise while a worker is still alive. Use bounded waits when joining (for example, repeat `join(timeout=0.2)` while alive).

**Example:** `run_pipeline(["CH1", "CH2"], 2, lambda channel: channel + ":PASS")` gives `["CH1:PASS", "CH2:PASS"]`. A failed CH1 still allows CH2 to finish before the failure reaches the caller.

**Watch out:** Store each job's input index alongside its result. Do not use `None` alone as a job; it is a valid input. Do not use `ThreadPoolExecutor` here: practice `Thread` and `Queue` directly.

**Reread:** threading docs, “Thread objects”; queue docs, “Queue objects” and the worker-thread example. For investigating a shutdown regression later, reread Pro Git 7.1, “Double Dot” and “Triple Dot”: a **revision** is a saved commit, and a **range** selects commits between revisions for `git log`. For example, `git log HEAD~3..HEAD` lists the last three commits on a straight history. As a companion investigation command, `git blame path` identifies the commits that last changed each line. No Git changes are required for this set.

Optional reading: *The Pragmatic Programmer*, topic on concurrency.


### E5 — Threads, processes and the GIL (easy, ~8 min)

**Goal:** Choose how to share instrument work safely between threads and processes. This is a concept check: return your answers rather than starting any workers.

**Signature:** `gil_answers() -> dict[str, str]`.

Return a dictionary with exactly the keys `"Q1"`, `"Q2"`, `"Q3"`, and `"Q4"`. Each value is the uppercase option letter (`"A"`, `"B"`, `"C"`, or `"D"`) you choose for that question.

**Example:** `sorted(gil_answers())` gives `['Q1', 'Q2', 'Q3', 'Q4']`. This shows the question IDs, not the answer letters.

A **process** is a running program with its own memory; threads within it share memory. **CPython** is the usual Python implementation, written in C, a compiled programming language. The **CPU** (central processing unit) performs calculations; a **core** is a CPU execution unit that can work independently of other cores. **Bytecode** is the sequence of instructions CPython executes for Python code. The **global interpreter lock (GIL)** is a lock used inside CPython to control that execution. These questions assume CPython with its GIL enabled; optional builds that disable it are outside this exercise.

**Q1.** Two station worker threads are doing calculations written in Python. What does the GIL mean for executing their Python bytecode within one process?

- **A.** Both threads execute Python bytecode at the same time if the computer has two processor cores.
- **B.** Only one thread executes Python bytecode at a time in that process.
- **C.** Only the main thread can execute Python bytecode; workers can only wait for instruments.
- **D.** A thread holds the GIL until it exits, so another thread cannot make progress before then.

<details>
<summary>Why it matters on the job — Q1</summary>
Choosing a worker design starts with understanding how the interpreter schedules station calculations.
</details>

**Serial** communication sends bytes through a device port; **VISA** (Virtual Instrument Software Architecture) is an interface used to communicate with test instruments.

**Q2.** Several instrument readers spend most of their time waiting on sockets, serial ports, or VISA replies. Why can threads still help even with the GIL?

- **A.** Starting a second instrument thread disables the GIL for the whole process.
- **B.** Each thread has a separate interpreter and its own GIL, even within the same process.
- **C.** Blocking I/O waits release the GIL, letting other threads run while a reader waits.
- **D.** Threads yield the GIL only when code explicitly calls Event.wait(); blocking instrument I/O alone cannot let another thread run.

<details>
<summary>Why it matters on the job — Q2</summary>
An operator display should remain responsive while multiple instruments take time to reply.
</details>

A **waveform** is a sequence of captured signal measurements; an **FFT** (fast Fourier transform) calculates its frequency content. **Multiprocessing** runs work in separate processes. A **C-backed library** performs some work in compiled C code; **NumPy** is one such library for numerical arrays.

**Q3.** FFT calculations on captured waveforms are CPU-heavy: calculation takes most of the time. Which approach can use multiple processor cores despite the GIL?

- **A.** Use multiprocessing, or a C-backed library such as NumPy whose relevant operations release the GIL.
- **B.** Add more threads running only Python bytecode; each thread automatically gets a separate processor core for simultaneous execution.
- **C.** Put calculations in a Queue; a Queue automatically starts a separate process for each item.
- **D.** Use an Event to start all Python calculation threads together; simultaneous starts bypass the GIL.

<details>
<summary>Why it matters on the job — Q3</summary>
Waveform analysis must finish quickly enough for the next station test step.
</details>

A **shared counter** is a number that several threads update. An **atomic** operation cannot be interleaved with another thread's operations partway through. A **Lock** lets one thread at a time enter a protected section of code; a Queue can instead send updates to one thread that owns the counter.

**Q4.** Two reader threads both do `count += 1` after receiving a measurement. Does the GIL make this shared counter update safe without coordination?

- **A.** Yes: the GIL makes every Python statement atomic, including `count += 1`.
- **B.** Yes: integer values cannot change in place, so updates to a shared integer cannot be lost.
- **C.** No, but calling `join()` on both readers afterward recovers any lost increments.
- **D.** No: `count += 1` is not atomic; protect updates with a Lock or send them through a Queue to one counter-owning thread.

<details>
<summary>Why it matters on the job — Q4</summary>
Lost measurement counts can make a station report disagree with the readings it collected.
</details>

**Watch out:** Return option letters, not option text. A single successful threaded run is not proof that a shared update is safe. No NumPy installation or instrument connection is needed for this quiz.

**Reread:** For Q1 and Q3, the Python glossary entry “global interpreter lock” and the threading docs introduction, “GIL and performance considerations”. For Q2, the same threading section on I/O-bound tasks (tasks that spend most of their time waiting for input/output). For Q4, threading docs, “Lock objects”, and queue docs, “Queue objects”.
