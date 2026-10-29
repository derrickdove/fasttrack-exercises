# d08 — Modules, packages, type hints and mypy

**Time:** about 57 minutes · **Read first:** [Python Tutorial §6: Modules and packages](https://docs.python.org/3/tutorial/modules.html), [§12: Virtual environments and packages](https://docs.python.org/3/tutorial/venv.html), [typing introduction](https://docs.python.org/3/library/typing.html), [mypy: Getting started](https://mypy.readthedocs.io/en/stable/getting_started.html), and [The Linux Command Line ch. 9: Permissions](https://linuxcommand.org/tlcl.php) · **You edit:** `starter/units/convert.py`, `starter/units/parse.py`, `starter/units/__init__.py`, `starter/units/guard.py`

## What you're building

A test station reads voltage, current, and resistance from instruments. Put its unit helpers in a reusable package so instrument drivers (code that communicates with instruments) and operator tools can share them. Check both the results and the type hints before these helpers reach station code.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/units/convert.py`, `starter/units/parse.py`, and `starter/units/guard.py`. For E3, replace the whole placeholder function in `starter/units/__init__.py` as explained below. Don't edit `tests/` or the empty `starter/__init__.py`.
2. Press **Ctrl+Shift+B → Test: d08** (or run `bash tools/run.sh d08` / `tools\run.ps1 d08` from the repo root). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **module** is a Python file; a **package** groups modules in a directory with an `__init__.py` file, which runs when the package is imported. An **import** makes another module's names available; a **relative import** starts with a dot to refer to the current package. This repo imports your package as `starter.units`.

A **type hint** describes an expected kind of value: `float` is a floating-point number and `str` is text. A **tuple** is a fixed sequence; `tuple[float, str]` describes a pair containing a number and text. `->` introduces the return type. **Static checking** examines code without running it; **mypy** is the checker here, and `--strict` enables its stricter checks. Hints do not validate instrument text while the program runs.

```python
# A separate example from an operator display module:
def channel_label(channel: int) -> str:
    return f"CH{channel}"

label: str = channel_label(2)
```

A **virtual environment** is a directory containing a project's Python interpreter and installed tools; the runner manages `.venv`. On Linux, **permissions** control who may read, write, or execute files. Importing a `.py` file needs read access and directory search access (the directory's execute permission); the `.py` file itself needs no execute permission when run through Python. These tests never change permissions.

## Exercises

### E1 — Convert an instrument reading (easy, ~10 min)

**Goal:** Return `(converted_value, base_unit)`. A **base unit** here means V (volts, voltage), A (amperes, current), or Ohm (ohms, resistance). A **prefix** scales a unit: milli is one thousandth, micro one millionth, kilo one thousand, and mega one million.

**Signature:** `def to_base(value: float, unit: str) -> tuple[float, str]`

| Input unit | Multiply value by | Returned unit |
| --- | --- | --- |
| `mV` | `0.001` | `V` |
| `kV` | `1000.0` | `V` |
| `mA` | `0.001` | `A` |
| `uA` | `0.000001` | `A` |
| `kOhm` | `1000.0` | `Ohm` |
| `MOhm` | `1000000.0` | `Ohm` |

**Example:** `to_base(4.7, "kOhm")` → `(4700.0, "Ohm")`.

**Watch out:** Accept exactly these six case-sensitive unit strings; do not trim whitespace. Every other unit, including `V`, `A`, and `Ohm`, raises `ValueError` (Python's exception for an unacceptable value). Preserve the sign and handle zero. Inputs are floats with no infinity or NaN (a special non-number value); you need not validate numeric types or guard against overflow. Return a float as the first tuple item. Use ASCII `u` for micro, not `µ`.

**Reread:** Python Tutorial §6.1, More on modules; typing introduction, function annotations.

### E2 — Parse an operator's quantity (medium, ~15 min)

**Goal:** A **quantity** is a number with its unit. Turn operator text into `(value, unit)` without converting the number to a base unit.

**Signature:** `def parse_quantity(text: str) -> tuple[float, str]`

**Examples:** `"4.7 kOhm"` → `(4.7, "kOhm")`; `"250mV"` → `(250.0, "mV")`; `"-3.3 V"` → `(-3.3, "V")`.

**Watch out:** The number may start with one `+` or `-`, followed immediately by a decimal number with at least one ASCII digit. Accept integers, `4.7`, `.5`, and `2.`; use a dot for the decimal point. Allow any whitespace before/after the quantity or between number and unit, including none. Never allow whitespace inside the number or unit. Supported units are exactly the six in E1 plus `V`, `A`, and `Ohm`, with the same spelling and case. Preserve the unit string and return a float. Raise `ValueError` for missing numbers/units, unsupported units, extra text, commas, exponent notation such as `1e3`, infinity, or NaN. Inputs are strings whose valid decimal values fit in a float.

You may use ordinary string processing or the standard library's `re` module for a **regular expression**, a text pattern. If using `re`, `fullmatch` requires the whole input to match; matching only its beginning would accept trailing junk. Keep E2 separate from conversion: `parse_quantity("250mV")` returns `250.0`, not `0.25`.

**Reread:** Python Tutorial §6, importing standard library modules; typing introduction, tuple return annotations.

### E3 — Publish the station helper package (easy, ~8 min)

**Goal:** **Re-export** means exposing a function from a module through its package. Make `from starter.units import to_base, parse_quantity` work, returning the original function objects from E1/E2.

**File:** `starter/units/__init__.py` (no new function).

**Example:** After the import above, `parse_quantity("2mA")` → `(2.0, "mA")`.

**Watch out:** Remove the entire supplied `__getattr__` placeholder (Python calls it when a package attribute is missing). Replace it with relative imports from `.convert` and `.parse`, and `__all__`: a list of public name strings used by `from package import *`. The list must contain exactly `"to_base"` and `"parse_quantity"`, once each, in either order. Export the original functions, without wrapper functions. Do not change the empty `starter/__init__.py`.

**Reread:** Python Tutorial §6.4, Packages; §6.4.1, Importing * from a package; §6.4.2, Intra-package references.

### E4 — Check the driver helper types (medium, ~12 min)

**Goal:** Keep the supplied function annotations and make every file in `starter/units/` pass `mypy --strict`. A function's **signature** describes its name, arguments, and return type. Hints on arguments, return values, and any collections you introduce should agree with the values used by your code.

**Signature:** Keep the exact E1/E2 signatures above. There is no additional function or file to create.

**Example:** A checker message like `convert.py:7: error: Incompatible return value type ... [return-value]` means line 7 returns something that disagrees with its `->` hint. The final bracket names the error category. Open that file at that line and compare the actual value to the expected type. If it says a function is missing an annotation, check its parameters and return annotation. Fix the first error and rerun; do not silence errors with `Any`, `# type: ignore`, or `# mypy: ignore-errors`.

**Watch out:** The tests run the current Python interpreter as `sys.executable -m mypy --strict` against your package, with a timeout. They also check the E1/E2 annotations. Because a function that only raises an exception can pass static checking, E4 calls E1/E2 first; implement those functions before expecting E4 to pass. Your completed code may already type-check: use this time to read each hint and confirm why it matches the implementation.

For a direct check from the repo root, run `.venv\Scripts\python.exe -m mypy --strict sets/d08/starter/units` on Windows or `.venv/bin/python -m mypy --strict sets/d08/starter/units` on Linux. Run the set first so the virtual environment exists. If Python says `No module named mypy`, check that you used the repo's `.venv` interpreter.

**Reread:** mypy Getting started, A quick intro to type hints and Next steps; Python Tutorial §12.1–12.2, Creating virtual environments and Managing packages; The Linux Command Line ch. 9, Reading, writing, and executing.

### E5 — Type hints don't stop bad values at runtime (easy–medium, ~12 min)

**Goal:** A power supply driver has an `enable_output(enable: bool)` method to turn its output on or off. A caller passed `2`. Write a check that the driver can call before sending an output command, then answer four questions about what type hints can catch. Work in `starter/units/guard.py`; no package re-export or driver method is required.

**Part A — Code (~4 min)**

**Signature:** `def require_bool(name: str, value: object) -> bool`

A **bool** is exactly `True` or `False`; an **int** is a whole number. The hint `object` accepts any Python value, so this helper can inspect an input whose type is not yet trusted. **Runtime** means while the program is executing. **Dynamic typing**, which Python uses, means values have types at runtime and operations check the types they need as they execute. **Static typing** checks type use before execution; mypy adds static checking to annotated Python code.

Return `value` unchanged if its type is exactly `bool`. For every other type, raise `TypeError` (Python's exception for an inappropriate type). The message must include the argument's `name` and the received type's name, such as `int` or `str`; the rest of the wording is up to you. `type(value)` gives the actual type, and `type(value).__name__` gives its name as text. Reject integers including `0`, `1`, and `2`, strings, `None` (the value meaning no value), floats, and every other non-bool value.

**Examples:** `require_bool("enable", True)` → `True`; `require_bool("enable", False)` → `False`; `require_bool("enable", 2)` raises `TypeError`, for example with the message `enable must be bool, got int`.

**Watch out:** `isinstance(value, int)` asks whether a value counts as an integer, and `isinstance(True, int)` is `True`: Python's bool type also counts as an int. Use `type(value) is bool` for this exact-type contract, or check for a bool before considering integer cases. Do not convert the input with `bool(value)`; conversion would accept bad inputs. In a condition, integer zero is false and other integers are true. A `bool` hint alone does not reject the caller's `2` at runtime. An **Enum** is a type with a fixed collection of named choices, such as output states ON and OFF; it can make a driver's allowed states clearer too. No Enum implementation is needed here.

**Part B — Concept check (~8 min)**

**Signature:** `def typing_answers() -> dict[str, str]`

A **dict** (dictionary) maps keys to values; `dict[str, str]` means both are strings. Return exactly the keys `"Q1"`, `"Q2"`, `"Q3"`, and `"Q4"`, each mapped to your chosen uppercase option letter (`"A"`, `"B"`, `"C"`, or `"D"`). Do not return the option text. Both parts count together as E5.

**Q1.** An operator script runs these lines directly in Python, without mypy. Which prediction fits Python's typing behavior?

```python
reading = 3.3
reading = "OVLD"
reading / 1000
```

- A. The first assignment fails because `reading` has no type hint.
- B. The division raises `TypeError`; removing that line lets both assignments run.
- C. The second assignment fails because the first assignment permanently fixed `reading` as a float.
- D. All three lines run because dynamic typing allows arithmetic with any combination of types.

<details>
<summary>Why it matters on the job</summary>

Knowing when checks happen helps you decide where a station should detect an invalid command.
</details>

**Q2.** Run this driver example directly in Python, without mypy; `commands` records what would be sent to the power supply. What happens as written, and in a fresh run with `enable = require_bool("enable", enable)` inserted before `commands.append` (using your completed Part A helper)?

```python
commands: list[str] = []

def enable_output(enable: bool) -> None:
    commands.append("OUTP 1" if enable else "OUTP 0")

enable_output(2)
```

- A. Both runs raise `TypeError` before entering the function because its parameter is annotated.
- B. The original appends `"OUTP 1"`; adding the helper converts `2` to `True` and appends the same command.
- C. The original appends `"OUTP 1"`; adding the helper raises `TypeError` and leaves `commands` empty.
- D. The original appends `"OUTP 0"` because `2` is not exactly `True`; adding the helper leaves `commands` empty.

<details>
<summary>Why it matters on the job</summary>

An operator tool's unexpected input should be handled before the driver sends an output command.
</details>

**Q3.** When you run mypy for the station's driver package, what does it do?

- A. It runs separately from the station program and checks source code against type hints without executing the driver.
- B. It imports and runs every driver method to discover which argument values the hardware accepts.
- C. It stays inside Python and checks each measurement's actual type whenever the station runs.
- D. It rewrites the driver to add runtime input checks at every annotated method.

<details>
<summary>Why it matters on the job</summary>

Knowing what a checker covers helps you choose the remaining tests for a driver.
</details>

**Q4.** Why should an output-on/off driver method accept a bool or an Enum of named states rather than a bare int (an integer with no named state)?

- A. Either annotation automatically prevents all invalid arguments from reaching the method at runtime.
- B. Either type automatically converts arbitrary integer inputs into valid on/off commands.
- C. Either type lets mypy check the instrument's physical output state while the station is running.
- D. Either type makes intended states clear to readers and static checkers; an explicit runtime check still rejects bad incoming values.

<details>
<summary>Why it matters on the job</summary>

A clear output-state contract helps callers avoid sending an unintended command to powered hardware.
</details>

**Watch out:** Keep both supplied signatures and use option letters exactly as shown. Quiz failures name the question and a reading to revisit; they do not supply its correct letter.

**Reread:** typing introduction, function annotations and runtime enforcement; mypy Getting started, A quick intro to type hints and Next steps.
