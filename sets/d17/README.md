# d17 — Driver design: a transport you can fake

**Time:** about 70 minutes · **Read first:** [typing.Protocol and structural typing](https://docs.python.org/3/library/typing.html#typing.Protocol); reread [d16: PyVISA, Communicating with your instrument](https://pyvisa.readthedocs.io/en/latest/introduction/communication.html); [abstract base classes (abc)](https://docs.python.org/3/library/abc.html); *The Pragmatic Programmer*, topic "Decoupling"; [Pro Git 5.2: Contributing to a Project](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project), especially "Commit Guidelines" · **You edit:** `starter/driver.py`, `starter/psu.py`

## What you're building

A chassis test station needs to read a meter and control a power supply before the instruments arrive. A **driver** translates station operations into instrument commands; a **transport** carries those commands and replies. You will pass a transport into each driver so the same driver can work with a fake today and connected hardware later.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `FakeTransport`, `Dmm`, and `PowerSupply` in `starter/driver.py`, and in `Psu` in `starter/psu.py`. Leave the supplied protocols unchanged. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d17** (or run `bash tools/run.sh d17` / `tools\run.ps1 d17`). At first you'll see `Exercises: 0 / 6 passed`. Rerun after each exercise.
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

### E5 - Build the bench power-supply driver (medium, ~15 min)

**Goal:** Implement `Psu` in the new `starter/psu.py`. This is the kind of problem the team asks in interviews. Leave E1-E4 in `starter/driver.py` as they are. `ResourceLike` and `ResourceManagerLike` are supplied protocols; do not implement or change them. The existing primer's general type-validation advice applies to E1-E4; E5-E6 add the explicit runtime checks below.

**Task sheet:** Write a Python driver for a bench **PSU** (power supply unit) that talks SCPI over **TCP/IP** (Transmission Control Protocol / Internet Protocol, a network communication system) through **PyVISA** (`pyvisa`, Python's interface to VISA, the Virtual Instrument Software Architecture). An **IP address** identifies an instrument on the network. Its VISA **resource name**, the string used to open a connection, has the form `TCPIP::<ip_address>::INSTR`; angle brackets mark a placeholder, not literal characters. This supply has one output. Its command sheet is:

| Command | Meaning / reply |
| --- | --- |
| `MEAS:VOLT?` | Read voltage; example reply `"12.034"` volts |
| `MEAS:CURR?` | Read current; example reply `"0.512"` **amps** (amperes, the unit of electric current) |
| `VOLT <n>` | Set output voltage to number `n` |
| `CURR <n>` | Set the **current limit**, the largest current the supply should deliver |
| `OUTP <0\|1>` | Disable output with `0`, enable it with `1` |

The sheet suggests `enable_output(enable: int)`. Our driver takes `bool` instead: callers must say `True` or `False`, so accidental values such as `2` cannot silently turn power on. Type hints do not enforce this at runtime. Python treats bool as a subclass of int (`isinstance(True, int)` is true), so an integer check alone accepts bools. Check the exact type where required below; **TypeError** reports a wrong type.

A VISA **resource manager** opens connections; a **message-based resource** is an open connection that exchanges text. Here is the small PyVISA **API** (application programming interface, the operations a library exposes) you need:

| Operation / attribute | Use |
| --- | --- |
| `pyvisa.ResourceManager()` | Create the default manager for connected hardware |
| `manager.open_resource(resource_name)` | Return an open resource |
| `resource.timeout` | Longest wait in **ms** (milliseconds); 2000 ms is 2 seconds |
| `resource.read_termination`, `resource.write_termination` | Characters marking the end of incoming/outgoing messages; set both to `"\n"` (newline) |
| `resource.write(command)` | Send text; returns the number of bytes written, which this driver ignores |
| `resource.read()` | Receive text; no command is sent |
| `resource.query(command)` | Send a command and return its reply text |
| `resource.close()` | Close the connection |

PyVISA calls this resource type `MessageBasedResource`. The supplied `ResourceLike` describes just the operations above. A **decorator** is an `@` modifier on a class or function. The supplied `@runtime_checkable` decorator allows `isinstance(resource, ResourceLike)` to check PyVISA's general resource type for **mypy**, a tool that checks type hints before you run the code. You do not need a VISA backend (the communication implementation) or hardware to complete these exercises: the tests inject fake managers and use **pyvisa-sim**, a simulated backend, once with `data/psu.yaml`. **YAML** is the text format used for that supplied device description; do not edit it.

**Signatures:** On `Psu`:

```python
def __init__(self, ip: str, timeout_ms: int = 2000, *,
             rm: ResourceManagerLike | pyvisa.ResourceManager | None = None,
             max_voltage: float | None = None,
             max_current: float | None = None) -> None: ...
def read_voltage(self) -> float: ...
def read_current(self) -> float: ...
def set_voltage(self, volts: float) -> None: ...
def set_current_limit(self, amps: float) -> None: ...
def enable_output(self, enable: bool) -> None: ...
```

The `*` makes following arguments **keyword-only**: pass them by name, such as `rm=manager`. `ResourceManagerLike | pyvisa.ResourceManager | None` accepts a matching fake manager, a real PyVISA manager, or `None`. E5 uses the default `None` safety limits; E6 adds their behavior to the same constructor and setters.

- Validate `timeout_ms` before opening anything: require a positive int, excluding bool. Otherwise raise `ValueError` naming `timeout_ms`.
- Open `f"TCPIP::{ip}::INSTR"` exactly once through the supplied `rm`. Only when `rm is None`, create `pyvisa.ResourceManager()` inside the constructor. **Lazy creation** means waiting until it is needed: importing the module or passing any manager must not create a default one. Keep the default manager alive while the resource is in use. Set the resource's `timeout` to `timeout_ms` and both termination attributes to `"\n"`. Construction sends no commands or queries. Use the supplied IP string without address-format validation.
- Each read method queries its sheet command exactly once on every call and returns `float(reply)`, a number that can have a fractional part. Ordinary float conversion accepts whitespace and scientific notation. Non-numeric text raises `ValueError` including the reply text; do not return a substitute reading.
- Each setter rejects negative values with `ValueError` before any write. Otherwise write exactly `f"VOLT {volts:.3f}"` or `f"CURR {amps:.3f}"` and return `None`. Formatting gives three digits after the decimal point. These setters make no query.
- `enable_output` requires an actual bool: everything else, including int `0` or `1`, raises `TypeError` before any write. Write exactly `"OUTP 1"` for `True`, `"OUTP 0"` for `False`, and return `None`.

**Example:** With a fake manager scripted with the sheet's replies, `supply = Psu("192.168.1.100", rm=manager)` opens `"TCPIP::192.168.1.100::INSTR"`. `supply.read_voltage()` returns `12.034`; `supply.read_current()` returns `0.512`. Calling `supply.set_voltage(12.0344)`, `supply.set_current_limit(0.5126)`, then `supply.enable_output(True)` writes `["VOLT 12.034", "CURR 0.513", "OUTP 1"]`.

**Watch out:** Validate before writing or rounding. Send command text without adding a newline yourself; the write termination handles it. Accept a compatible manager without requiring it to inherit from the supplied protocol. Except for the documented validation, let communication errors reach the caller unchanged. There are no extra type checks on voltage/current arguments beyond their annotations.

**Reread:** The day's `typing.Protocol` reading, structural subtyping and `runtime_checkable`; reread d16's PyVISA *Communicating with your instrument*, `ResourceManager.open_resource`, `MessageBasedResource`, timeouts, terminations, `write`, `read`, `query`, and `close`.

### E6 - Configure limits and clean up safely (medium, ~10 min)

**Goal:** Extend `Psu` so a station configuration controls its limits and a failed test step still releases the instrument. This exercise builds on E5.

**Signatures:** Add these methods to `Psu` and finish the constructor's keyword-only `max_voltage` and `max_current` arguments:

```python
@classmethod
def from_config(cls, path: str | Path, *,
                rm: ResourceManagerLike | pyvisa.ResourceManager | None = None) -> Psu: ...
def close(self) -> None: ...
def __enter__(self) -> Psu: ...
def __exit__(self, exc_type: type[BaseException] | None,
             exc_value: BaseException | None,
             traceback: TracebackType | None) -> Literal[False]: ...
```

A **class method** receives the class as `cls` instead of an instance as `self`; call it as `Psu.from_config(path, rm=manager)` and construct `cls(...)` inside it. `Path` is a filesystem path object from `pathlib`; accept a string path too. **TOML** is a text format for settings written as `key = value`. Use the standard-library `tomllib.load` with the file opened in binary mode (`"rb"`, reading bytes rather than decoded text). The file uses these top-level keys (no section headings):

```toml
ip = "192.168.1.100"
timeout_ms = 750
max_voltage = 12
max_current = 0.5
```

- `ip` is required and must be a str. Optional `timeout_ms` defaults to `2000` and must be a positive int, excluding bool. Optional `max_voltage` and `max_current` must be numbers (int or float, excluding bool); if omitted, each defaults to `None`, meaning no maximum. A missing required key or wrong-typed key raises `ValueError` naming that key. Validate the entire configuration before opening the resource, then forward all settings and `rm` to `cls`. Ignore extra keys. File-access and TOML syntax errors may reach the caller unchanged.
- Retain the two constructor maxima. `set_voltage` above `max_voltage`, or `set_current_limit` above `max_current`, raises `ValueError` naming the maximum's key and value before any write. Equality is allowed, zero is a real limit, and `None` removes that limit. Check before rounding: `12.0001` exceeds a maximum of `12`. Keep E5's negative-value checks.
- `close()` closes the resource once and returns `None`; repeated calls do nothing. Explicit `close()` sends no output command. Do not close the manager: other drivers may share it.

A **context manager** is an object used in a `with` statement to arrange entry and cleanup. Python calls `__enter__` before the block; return `self` so `with supply as active:` gives the block that supply. It calls `__exit__` after the block, even when the block raises an exception. Its three arguments describe that exception (all are `None` after normal completion); `TracebackType` describes the record of where it occurred. `Literal[False]` means the return value is always `False`, so Python continues raising the block's exception.

In `__exit__`, first attempt `"OUTP 0"`, then always close the resource, even if that write fails; `try`/`finally` ensures the close is attempted. If the block raised, preserve that original exception even if cleanup also raises an ordinary exception. After a successful block, let a cleanup failure reach the caller. Context cleanup sends no other commands. Re-entering an already closed supply and operations after close are outside this exercise.

**Example:** With `path` containing the TOML above and a fake manager, the following code writes `["VOLT 12.000", "CURR 0.500", "OUTP 1", "OUTP 0"]` and closes the resource once:

```python
with Psu.from_config(path, rm=manager) as supply:
    supply.set_voltage(12)
    supply.set_current_limit(0.5)
    supply.enable_output(True)
```

With the same configuration, requesting `supply.set_voltage(12.0001)` inside the block raises `ValueError` mentioning `max_voltage` and `12`, before sending a voltage-setting command; output-off and close still run on exit.

**Watch out:** Do not use **truthiness** (whether an `if` treats a value as true or false) to detect a maximum: zero must still be enforced. Do not return `True` from `__exit__`, which would hide a failed test step.

**Reread:** The day's `typing.Protocol` reading; reread d16's PyVISA *Communicating with your instrument*, connection lifetime and `close`. For the new syntax, see the Python reference on [class methods](https://docs.python.org/3/library/functions.html#classmethod), [tomllib](https://docs.python.org/3/library/tomllib.html), and [context managers](https://docs.python.org/3/reference/datamodel.html#context-managers).
