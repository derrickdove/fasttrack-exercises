# d33 — Processes, exit codes and signals

**Time:** about 45 minutes (41 coding + 4 review) · **Read first:** [Missing Semester, Command-line Environment](https://missing.csail.mit.edu/2020/command-line/) (job control and signals); Python [subprocess](https://docs.python.org/3/library/subprocess.html) and [signal](https://docs.python.org/3/library/signal.html) docs; **Review for tomorrow's day-34 check: your weakest set so far** — look at your tracker and redo the set you marked partial or stuck most recently. · **You edit:** `starter/procs.py`

## What you're building

A chassis test station starts instrument-check tools, records whether they succeeded, and retries tools that fail. It also needs to notice an operator's stop request so the station can finish cleanup before shutting down.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/procs.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d33** (or run `bash tools/run.sh d33` / `tools\run.ps1 d33`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker. Spend the final four minutes revisiting your most recently partial or stuck set for tomorrow's day-34 check; if you need longer, continue that review after this set.

A **process** is a running program; a **child process** is one started by your Python program. An **argument list** contains the executable path followed by its separate arguments. A **shell** interprets command text; passing a list with `shell=False` (the default) avoids that extra interpreter.

An **exit code** is the integer a process returns when it finishes; zero conventionally means success. **Standard output** (`stdout`) carries normal text; **standard error** (`stderr`) carries diagnostic text. **Capture** means returning that text to Python instead of displaying it. A **timeout** is the maximum number of seconds allowed for one run.

A **signal** is a notification delivered to a process. **SIGINT** is the interrupt request normally sent by Ctrl+C; **SIGTERM** is a termination request commonly sent by service managers. A **handler** is a function called when a signal arrives. **Job control** is the shell's ability to stop, resume, and manage running processes.

A **context manager** supplies setup and cleanup for a `with` block through `__enter__` and `__exit__`. A **flag** is a Boolean value recording whether something happened. Here, **graceful stopping** means recording the request now so normal code can perform cleanup later.

```python
import sys

args = [sys.executable, "-c", "print('Station B7 ready')"]
# sys.executable is this Python interpreter's path.
# -c makes Python execute the following argument as code.
```

## Exercises

### E1 — Capture an instrument check (easy, ~11 min)

**Goal:** Run an instrument-check tool with `subprocess.run`. Return `(returncode, stdout, stderr)` as an integer and two strings. Use `capture_output=True`, `text=True`, and the supplied timeout in seconds. Keep output exactly as returned, including trailing newlines. A nonzero exit code is a result, so do not use `check=True` (which would raise an exception for failure).

**Signature:** `def run_tool(args: list[str], timeout: float) -> tuple[int, str, str]`

**Example:** `run_tool([sys.executable, "-c", "print('PASS')"], 2.0)` → `(0, "PASS\n", "")`

**Watch out:** `args` is a nonempty argument list; do not modify it or join it into shell text. `timeout` is positive. On `subprocess.TimeoutExpired`, return exactly `(-9, "", "timeout")`, discarding any partial output. `subprocess.run` already kills the child and waits for it before raising that exception; no separate kill call is needed. The `-9` is our station's timeout marker on every platform. Other exceptions, such as `FileNotFoundError` for a missing executable, must propagate to the caller. No input validation beyond these stated cases is needed.

**Reread:** Python `subprocess` docs, “Using the subprocess Module”: `run`, `CompletedProcess`, and `TimeoutExpired`.

### E2 — Explain the tool result (easy, ~6 min)

**Goal:** Convert a recorded code to the exact operator-facing text below. In this exercise a shell-style code greater than 128 encodes a signal as `128 + signal_number`. Python's `Popen` process object uses negative codes for signal termination on POSIX systems (such as Linux); decode those as the positive signal number too. This is a decoding convention, not proof that an arbitrary tool's code came from a signal.

**Signature:** `def exit_code_meaning(code: int) -> str`

| Code | Return text |
| --- | --- |
| `0` | `"ok"` |
| `1` | `"fail"` |
| `2` | `"usage"` (the tool was called incorrectly) |
| Negative | `"killed by signal N"`, where `N = -code` |
| Greater than `128` | `"killed by signal N"`, where `N = code - 128` |
| `3` through `128`, inclusive | `"exit N"`, where `N = code` |

**Example:** `exit_code_meaning(143)` → `"killed by signal 15"`; `exit_code_meaning(-15)` → the same string.

**Watch out:** `128` itself is `"exit 128"`. Use decimal numbers, not signal names. Accept any integer; do not validate whether a decoded signal exists on this machine.

**Reread:** Python `subprocess` docs, `Popen.returncode`; Missing Semester, Command-line Environment → “Job Control” / “Killing a process”.

### E3 — Record an operator stop request (medium, ~15 min)

**Goal:** Implement `GracefulStop`, a context manager with a public Boolean `requested` flag. Construction sets `requested=False`. Each entry resets it to `False`, saves the current SIGINT handler and the SIGTERM handler where available, installs `_handle` for those signals, and returns `self`. `_handle(signum, frame)` sets `requested=True` and returns normally. `signum` is the signal number; `frame` describes the interrupted Python execution and is unused here.

**Signatures:** `GracefulStop()`, `__enter__(self) -> GracefulStop`, `_handle(self, signum: int, frame: FrameType | None) -> None`, and the supplied `__exit__(...) -> None`.

**Example:**

```python
with GracefulStop() as stop:
    assert stop.requested is False
    signal.raise_signal(signal.SIGINT)
    assert stop.requested is True
```

**Watch out:** `signal.getsignal` reads an existing handler; `signal.signal` replaces it. Restore the exact saved handlers on exit, including when the block raises an exception. Let that exception propagate; `__exit__` returns `None`. Its three arguments describe the exception (or are all `None` on normal exit). Restoring handlers does not reset `requested`; the flag keeps its last value until the next entry. Sequential reuse and nested blocks with *different* `GracefulStop` instances must work. Re-entering the same instance before it exits is outside scope. Calls happen on Python's main thread (the thread where the program started), where installing handlers is allowed. Do not exit, print, or raise in the handler. The tests use `signal.raise_signal`, which delivers a signal to the current process without an external command.

**Reread:** Python `signal` docs, “Execution of Python signal handlers”, “Signals and threads”, `getsignal`, `signal`, and `raise_signal`; Missing Semester, “Job Control”.

### E4 — Restart a failed station tool (medium, ~9 min)

**Goal:** A **supervisor** starts a program and decides whether to restart it. Implement a small version of systemd's `Restart=on-failure` idea; systemd is a Linux service manager that starts and monitors background programs. Call E1's `run_tool(cmd, timeout=5.0)` on each attempt. Collect only the exit codes, in order. Stop immediately on code `0`, or once the retry budget is exhausted.

**Signature:** `def supervise(cmd: list[str], restarts: int) -> list[int]`

**Example:** With `restarts=2`, a tool that fails twice and then succeeds returns `[1, 1, 0]`. A tool that keeps failing returns `[1, 1, 1]`. A tool that succeeds immediately returns `[0]`.

**Watch out:** `restarts` counts additional tries, so zero still permits one attempt. Negative `restarts` raises `ValueError` before launching anything. Any nonzero code, including E1's `-9` timeout marker, consumes an attempt and permits another if budget remains. Use the same `cmd` each time; do not add a delay or change its arguments. Discard the output strings. Other errors from E1 propagate instead of being retried. Finish E1 first; E4 reuses it.

**Reread:** Python `subprocess` docs, `run` and `CompletedProcess.returncode`; Missing Semester, “Job Control”. For tomorrow's check, revisit your most recently partial or stuck set in the tracker.

## Terminal drill (WSL2 Ubuntu, ~5 min)

This drill is ungraded; its minutes come from the day's readings. Finish E3 first. In Ubuntu terminal A, from the repo root, run this **worker** (a process that waits for work or a stop request):

```bash
.venv/bin/python - <<'PY'
import os
import sys
import time

sys.path.insert(0, "sets/d33")
from starter.procs import GracefulStop

with GracefulStop() as stop:
    print(f"worker PID: {os.getpid()}", flush=True)
    try:
        while not stop.requested:
            time.sleep(0.1)
    finally:
        print("cleanup: station work stopped", flush=True)
print("worker exited; previous signal handlers restored", flush=True)
PY
```

`-` makes Python read code from standard input; `<<'PY'` feeds it the lines up to the closing `PY`. `sys.path.insert` lets Python find this set's `starter` module. A **PID** is the operating system's process identifier; `os.getpid()` prints this worker's PID after its handlers are installed. `flush=True` displays the message immediately. `time.sleep(0.1)` pauses briefly between flag checks; `finally` runs cleanup when the loop ends. Here cleanup is represented by a message; real station code would close instrument connections there.

In another Ubuntu terminal, replace `<pid>` below with the printed number (omit the angle brackets). `ps` displays that process and its command; `kill -TERM` sends it SIGTERM:

```bash
ps -p <pid> -o pid,comm,args
kill -TERM <pid>
```

Watch terminal A print the cleanup and exit messages, then return to its shell prompt. The handler only sets `requested`; the loop notices it, runs cleanup, and leaves the context manager, which restores the previous handlers. Ctrl+C in terminal A also requests a graceful stop if you need to end the drill.
