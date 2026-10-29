# d17 — Driver design: a transport you can fake

**Time:** about 45 minutes · **Read first:** [typing.Protocol and structural typing](https://docs.python.org/3/library/typing.html#typing.Protocol); [abstract base classes (abc)](https://docs.python.org/3/library/abc.html); *The Pragmatic Programmer*, topic "Decoupling"; [Pro Git 5.2: Contributing to a Project](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project), especially "Commit Guidelines" · **You edit:** `starter/driver.py`

## What you're building

A chassis test station needs to read a meter and control a power supply before the instruments arrive. A **driver** translates station operations into instrument commands; a **transport** carries those commands and replies. You will pass a transport into each driver so the same driver can work with a fake today and connected hardware later.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `FakeTransport`, `Dmm`, and `PowerSupply` in `starter/driver.py`. Leave the supplied `Transport` interface unchanged. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d17** (or run `bash tools/run.sh d17` / `tools\run.ps1 d17`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **protocol** describes the methods an object must offer; matching objects do not need to inherit from it. An **abstract base class** is an alternative that can require subclasses to implement methods. This set uses a protocol.

**Decoupling** means keeping parts independent: the driver knows the transport's methods, without knowing how it connects. **Dependency injection** means passing a needed object into a constructor (`__init__`, which runs when you create an object).

A **fake** is a small replacement for a real component. A **dictionary** maps keys (here, command strings) to values (reply strings); a **list** stores items in order. A **scripted reply** is a predetermined answer stored under a command in a dictionary. A **write** sends a command without a reply; a **query** sends a command and returns reply text.

```python
from typing import Protocol

class StationLog(Protocol):
    def record(self, text: str) -> None: ...
# Any object with a matching record method can serve as a StationLog.
```

**SCPI** (Standard Commands for Programmable Instruments) is a text command language. Here `*IDN?` asks an instrument to identify itself; `INST:NSEL` selects a numbered channel (an independently controlled supply connection). Commands must match the documented text exactly: no extra spaces, newline characters, or commands.

The annotations (`str`, `int`, `float`, `bool`) describe the input types callers supply. You do not need general type validation. `None` means a method returns no value. `KeyError` means a dictionary key is missing; `ValueError` means a value is unacceptable. Let errors from the transport and numeric conversion reach the caller; do not catch or replace them.

## Exercises

### E1 — Script a bench transport (easy, ~10 min)

**Goal:** Implement `FakeTransport` so station tests can use instruments without hardware. The supplied `Transport(Protocol)` requires `write(command: str) -> None` and `query(command: str) -> str`.

**Signatures:** `FakeTransport(replies: dict[str, str])`, `write(command: str) -> None`, `query(command: str) -> str`.

Construction sends nothing and creates a new public `writes: list[str]`, initially empty, for each instance. Store the replies dictionary for lookup; tests do not modify it after construction. `write` appends the exact command to `writes`, in call order, including duplicates or empty strings, and returns `None`. `query` returns the dictionary value for that exact command without stripping it or consuming it. An unknown query raises `KeyError`. Queries never add to `writes`, even when they fail.

**Example:** With `fake = FakeTransport({"*IDN?": "BenchMeter\n"})`, `fake.query("*IDN?")` returns `"BenchMeter\n"`; after `fake.write("CONF:VOLT:DC")`, `fake.writes` is `["CONF:VOLT:DC"]`.

**Watch out:** Each fake needs its own write history. A query does not implicitly call `write` in this interface.

**Reread:** `typing.Protocol`, the structural typing example; `abc`, the `abstractmethod` description, to compare the two approaches.

### E2 — Read the station meter (easy, ~10 min)

**Goal:** Implement `Dmm`, a **digital multimeter** (DMM: an instrument that measures electrical quantities). **DC voltage** is electrical potential with a fixed polarity; **V** means volts, its unit.

**Signatures:** `Dmm(transport: Transport)`, `idn() -> str`, `measure_dc_voltage() -> float`.

Keep the supplied transport in the constructor without sending anything. `idn()` queries `"*IDN?"` exactly once and returns its reply with leading and trailing whitespace removed. `measure_dc_voltage()` queries `"MEAS:VOLT:DC?"` exactly once and returns `float(reply)`. Neither method calls `write`. Every call must query again, rather than reuse a previous result. Text that cannot be converted to a float raises `ValueError`; a missing scripted reply raises `KeyError`.

**Example:** A reply of `"  +1.250E+1\r\n"` to `"MEAS:VOLT:DC?"` produces `12.5`.

**Watch out:** Accept any object with the protocol's two methods, including one that never inherits from `Transport` or `FakeTransport`. Do not construct a replacement transport.

**Reread:** `typing.Protocol`, structural subtyping; *The Pragmatic Programmer*, "Decoupling", separating responsibilities.

### E3 — Set a supply voltage safely (medium, ~13 min)

**Goal:** Implement the power supply constructor and voltage setting. Validate the whole request before changing the station's instrument state.

**Signatures:** `PowerSupply(transport: Transport)`, `set_voltage(ch: int, v: float) -> None`.

Keep the supplied transport without sending anything in the constructor. Valid channels are 1, 2, and 3. Valid voltage is finite and in the inclusive range 0–30 V. Non-finite values (positive/negative infinity and NaN, meaning "not a number") are invalid. If either argument is invalid, raise `ValueError` before any transport write or query, preserving existing history.

For a valid request, write `f"INST:NSEL {ch}"` followed by `f"VOLT {v:.3f}"`, and return `None`. The `:.3f` format rounds to exactly three digits after the decimal point. Do not query.

**Example:** `supply.set_voltage(2, 5.1256)` writes `["INST:NSEL 2", "VOLT 5.126"]`.

**Watch out:** Validate before rounding: `30.0001` is invalid even though formatting would display `30.000`. A bad voltage must not select a channel first.

**Reread:** `typing.Protocol`, using a protocol as a parameter type; Pro Git 5.2, "Commit Guidelines" on logically separate changes and clear messages. If keeping local commits, finish this behavior as one small change; commits are not graded.

### E4 — Switch and measure supply channels (medium, ~12 min)

**Goal:** Add operations that an operator's station procedure can combine in a predictable order.

**Signatures:** `output(ch: int, on: bool) -> None`, `measure_voltage(ch: int) -> float`, both on `PowerSupply`.

Both methods require channel 1, 2, or 3; otherwise raise `ValueError` before any write or query. Every valid call first writes `f"INST:NSEL {ch}"`, even if the previous call selected the same channel.

- `output` then writes `"OUTP ON"` for `True` or `"OUTP OFF"` for `False`, makes no query, and returns `None`.
- `measure_voltage` then queries `"MEAS:VOLT?"` exactly once and returns `float(reply)`. Its only write is channel selection. Invalid numeric reply text raises `ValueError`; a missing reply raises `KeyError`. In these reply-error cases, selection has already been written.

**Example:** `supply.output(3, True)` followed by `supply.measure_voltage(3)` writes `["INST:NSEL 3", "OUTP ON", "INST:NSEL 3"]`, then queries `"MEAS:VOLT?"`. A reply of `" 3.300\n"` returns `3.3`.

**Watch out:** Keep operation order exact. A failed measurement must not be converted into a plausible voltage such as zero.

**Reread:** *The Pragmatic Programmer*, "Decoupling"; Pro Git 5.2, "Commit Guidelines", keeping a change focused enough to review.
