# d16 - PyVISA and a simulated instrument

**Time:** about 45 minutes | **Read first:** [PyVISA: Communicating with your instrument](https://pyvisa.readthedocs.io/en/latest/introduction/communication.html), [Missing Semester: Command-line Environment (job control, dotfiles, SSH)](https://missing.csail.mit.edu/2020/command-line/), and [PyVISA-sim documentation](https://pyvisa-sim.readthedocs.io/en/latest/) | **You edit:** `starter/visa_basics.py`

## What you're building

A chassis test station must find its instruments, record their identities, and read voltage before it can judge a hardware test. You will use a **DMM** (digital multimeter, an instrument that measures electrical quantities) and a **PSU** (power supply unit, an instrument that provides electrical power). Both are simulated here, so you need no hardware or network connection.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/visa_basics.py`. Don't edit `tests/` or the supplied `data/station.yaml`.
2. Press **Ctrl+Shift+B -> Test: d16** (or run `bash tools/run.sh d16` / `tools\run.ps1 d16`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

**VISA** (Virtual Instrument Software Architecture) is a common interface for talking to instruments; **PyVISA** is its Python interface. A **backend** is the implementation handling those communications; **pyvisa-sim** supplies a simulated backend instead of real hardware. **YAML** is a text format for structured settings; the supplied YAML file defines fixed command/reply pairs.

A **resource name** is an instrument's VISA address. `GPIB0::8::INSTR` identifies instrument 8 on controller 0 of **GPIB**, a laboratory instrument bus. A **resource manager** discovers and opens resources. A **session** is an open connection; the supplied `MessageBasedResource` type represents a resource that exchanges text commands and replies.

**SCPI** (Standard Commands for Programmable Instruments) is a text command language used by many instruments. A **query** sends a command and reads its reply; in PyVISA, `resource.query(command)` returns a string. **Termination** is the character marking the end of a message; `"\n"` means newline. A **timeout** limits how long communication waits; 2000 **ms** (milliseconds) is two seconds.

A **dictionary** maps keys to values; `dict[str, str]` means both are strings. A **float** represents a number with a fractional part. `strip()` removes surrounding whitespace, and `split(separator)` divides text into a list. For example, an operator log can be broken into two fields:

```python
entry = " CH2 ; PASS "
fields = entry.split(";")
channel = fields[0].strip()
status = fields[1].strip()
```

The tests supply open resources directly to E2 and E3, so those exercises do not depend on your E1 implementation. They also use small stand-ins for instruments to check replies that the supplied simulator does not produce.

## Exercises

### E1 - Open an instrument session (easy, ~13 min)

**Goal:** Open the operator's requested instrument through the supplied simulator file.

**Signature:** `def open_resource(resource_name: str, sim_file: str) -> MessageBasedResource`

Construct `pyvisa.ResourceManager(f"{sim_file}@sim")` and open `resource_name` through it. `sim_file` is a string containing a filesystem path to a simulator YAML file, without the `@sim` suffix; paths may contain spaces. Return the open instrument with `read_termination` and `write_termination` both equal to `"\n"`, and `timeout` equal to `2000`. Set these attributes through `manager.open_resource(..., read_termination=..., write_termination=..., timeout=...)` or on the returned resource.

**Example:** With `sim_file` pointing to `data/station.yaml`, `open_resource("GPIB0::8::INSTR", sim_file)` returns the DMM session. Its `query("*IDN?")` returns `"Fasttrack,DMM-100,DMM001,1.0"`.

**Watch out:** Use the supplied file, not the default `"@sim"` devices. Return the instrument, not the manager. Keep the session and manager open on success; closing a manager also closes its instrument sessions. The caller owns cleanup: call `resource.close()` after use. At station shutdown, `pyvisa.ResourceManager(f"{sim_file}@sim").close()` closes the shared manager; do that only after all sessions using that backend are finished. A `VisaIOError` reports a VISA backend or communication failure; let backend errors reach the caller unchanged. Inputs name message-based instruments such as this station's DMM and PSU.

**Reread:** PyVISA, *Communicating with your instrument*, the `ResourceManager`, `open_resource`, termination, and timeout examples; PyVISA-sim documentation, using your own device definition with `path/to/file.yaml@sim`.

### E2 - Record instrument identity (easy/medium, ~12 min)

**Goal:** Turn an instrument identity reply into fields for the station's test report.

**Signature:** `def identify(resource: MessageBasedResource) -> dict[str, str]`

Query `"*IDN?"` exactly once. Split the reply on commas and strip surrounding whitespace from every field. Require exactly four nonempty fields in this order: manufacturer, model, serial, firmware. A **serial number** identifies one physical unit; **firmware** is the instrument's embedded software version. Return a dictionary with exactly the keys `"manufacturer"`, `"model"`, `"serial"`, and `"firmware"`, keeping every value as a string.

**Example:** A reply of `" Lab , DMM X , 00042 , rev 3 \n"` becomes `{"manufacturer": "Lab", "model": "DMM X", "serial": "00042", "firmware": "rev 3"}`.

**Watch out:** Raise `ValueError` (Python's invalid-value exception) if the reply has too few or too many fields, or any field is empty after stripping. Preserve spaces inside fields and leading zeroes in serial numbers. Do not close the resource. Let communication errors reach the caller unchanged.

**Reread:** PyVISA, *Communicating with your instrument*, the `query` and `*IDN?` examples. Compare the supplied YAML's `dialogues` entries (command/reply pairs) with the PyVISA-sim documentation's device-definition examples.

### E3 - Read the station voltage (easy, ~8 min)

**Goal:** Return a measurement in **volts** (the unit of electrical voltage) for a later test step to check against its limits. **DC** means direct current, used here to distinguish a steady voltage measurement from an alternating signal.

**Signature:** `def read_voltage(resource: MessageBasedResource) -> float`

Query `"MEAS:VOLT:DC?"` exactly once and return `float(reply)`. Both supplied instruments support this command: the DMM replies with `"+2.500000E+00"` (2.5 volts), and the PSU replies with `"+1.200000E+01"` (12.0 volts). This **scientific notation** uses `E` to express a power of ten.

**Example:** A reply of `" -1.25e-3\n"` returns `-0.00125`.

**Watch out:** Keep negative signs and fractional values. Use Python's ordinary float conversion; it handles surrounding whitespace and scientific notation. Invalid numeric text such as `"OVERLOAD"`, `"5 V"`, or an empty reply must raise `ValueError`. Let communication errors reach the caller unchanged. Do not close the resource, retry, or apply pass/fail limits here.

**Reread:** PyVISA, *Communicating with your instrument*, querying an instrument and converting returned text to numbers; PyVISA-sim documentation, fixed replies in device dialogues.

### E4 - Discover instruments for the operator (easy, ~12 min)

**Goal:** Build a repeatable list of instrument addresses for an operator tool.

**Signature:** `def list_instruments(sim_file: str) -> list[str]`

Create a resource manager using `f"{sim_file}@sim"`. Call its `list_resources()` with no arguments, sort the returned names using Python's normal string ordering, and return a list of those names. Close this function's manager before returning; use `try`/`finally` or `with closing(pyvisa.ResourceManager(...)) as manager:`. The supplied `closing` helper makes a **context manager**, an object used by `with` to call `close()` when its block ends, even if an error occurs. Return `[]` when discovery returns no resources.

**Example:** With the supplied station file, return `["GPIB0::12::INSTR", "GPIB0::8::INSTR"]`. String sorting puts `"12"` before `"8"`; do not sort addresses numerically.

**Watch out:** Discover resources rather than hard-coding this file's two names. Alternate files may define different resources. Some backends raise `VisaIOError` when no instruments match; let that error reach the caller too. Return `[]` if `list_resources()` returns an empty collection. Discovery does not need to open or query instruments. PyVISA shares managers for the same backend, so perform discovery before opening measurement sessions with E1. Repeated discovery must work. Let backend/file errors reach the caller.

**Reread:** PyVISA, *Communicating with your instrument*, the `ResourceManager` and `list_resources` examples; PyVISA-sim documentation, the `resources` mapping. In Missing Semester, *Command-line Environment*, reread Job Control: backgrounding a station process does not close its instrument sessions. Its dotfiles (shell configuration files) and SSH (Secure Shell, remote terminal access) sections explain the environment an operator might run this tool from; no shell scripting is required here.
