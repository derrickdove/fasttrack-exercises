# d01 — Placement check: read an instrument's reply

**Time:** about 45 minutes (8 minutes to check setup and report, 37 minutes of exercises) · **Read first:** [Python Tutorial §3: An Informal Introduction to Python — numbers, strings and lists](https://docs.python.org/3/tutorial/introduction.html), [Missing Semester lecture 1: The Shell](https://missing.csail.mit.edu/2020/course-shell/) · **You edit:** `starter/replies.py`

## What you're building

A **test station** is a computer and connected equipment used to check hardware; an **instrument** is equipment that measures or controls something, such as a meter or power supply. Your station must turn an instrument's text replies into usable Python values and prepare a voltage command for an **operator**, the person running the station. This **placement check**, a check of your current skills, tells you which topics need more practice; you do not need real equipment.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/replies.py`. Don't edit `tests/`. A `NotImplementedError` marks an unfinished function.
2. Press **Ctrl+Shift+B → Test: d01** (or run `bash tools/run.sh d01` / `tools\run.ps1 d01` from the repo folder). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise. The tests use **pytest**, a tool that runs Python checks for you.
3. Report **all pass / partial / stuck** in the tracker. Note which exercises took longest and where you got stuck: those topics get extra attention. If you reach 45 minutes, report your current result.

A **shell** is a program that runs commands you type. Check that you opened the exercises repo folder; in the shell reading, `pwd` shows the current folder and `cd` changes folders. If setup still fails, use the repo README's troubleshooting steps and include the first error in your report.

A **function** is named code you call with input values; its **signature** lists its name, inputs and output type. The **type hints** after `:` and `->` describe those types: `str` is text, `int` is a whole number, and `float` is a number that can have a fractional part.

A **list** is an ordered collection; `list[int]` means a list of integers.
A **dictionary** stores values under names called keys; `dict[str, str]` means text keys and text values.
**Whitespace** means spaces, tabs and line endings; `\n` is a newline and `\r\n` is a common two-character line ending.
`ValueError` is Python's error for an input value the function cannot accept; use `raise ValueError("explanation")` when a contract requires it.

```python
label = "  bench 7\n"
clean = label.strip()            # "bench 7": remove whitespace at the edges
fields = "CH2;READY".split(";")  # ["CH2", "READY"]: split at a separator
status = {"channel": fields[0]}  # look up status["channel"] to get "CH2"
message = f"Station: {clean}"    # an f-string inserts values into text
```

**SCPI** means Standard Commands for Programmable Instruments: text commands and replies used by many instruments. Here, commas separate fields and channels, and a colon separates the start and end of a channel range. Each function handles one string; do not read files, print results or contact equipment. Inputs have the types shown in the signatures.

## Exercises

### E1 — Identify the station's meter (easy, ~8 min)

**Goal:** Turn an **identification reply**, the meter's description of itself, into named Python values. Turning structured text into values is called **parsing**. The four fields are its manufacturer, model, serial number (the individual unit's identifier) and firmware (the software version inside the meter).

**Signature:** `def parse_idn(reply: str) -> dict[str, str]`

**Example:**

```python
parse_idn("KEYSIGHT TECHNOLOGIES,34461A,MY57212345,A.03.01\n")
# {"manufacturer": "KEYSIGHT TECHNOLOGIES", "model": "34461A",
#  "serial": "MY57212345", "firmware": "A.03.01"}
```

**Contract:** Split on commas. Require exactly four fields and return exactly the keys `manufacturer`, `model`, `serial` and `firmware`, in that field order. Remove whitespace at each field's edges; preserve internal spaces and capitalization. Empty fields are allowed: `",,,"` produces four empty values. Raise `ValueError` if the field count is not four, including an entirely empty reply. Quoted commas have no special meaning.

**Watch out:** A trailing newline belongs to the last field's whitespace; it is not a fifth field. An extra comma does create another field.

**Reread:** [Python Tutorial §3.1.2, Text](https://docs.python.org/3/tutorial/introduction.html#text) for strings and indexing (selecting an item by its position); [Missing Semester, Navigating in the shell](https://missing.csail.mit.edu/2020/course-shell/#navigating-in-the-shell) if locating the starter file slowed you down.

### E2 — Read a measured value (easy, ~7 min)

**Goal:** Convert a meter's numeric reply into a `float`. **Scientific notation** uses `e` or `E` for a power of ten: `-4.5e-3` means `-0.0045`. An **overload** means the reading exceeded the instrument's measurement range; this meter signals it with the number `9.9e37`.

**Signature:** `def parse_reading(text: str) -> float`

**Examples:** `"+1.23456789E+00"` → `1.23456789`; `"-4.5e-3\r\n"` → `-0.0045`; `" 12 "` → `12.0`; `"+9.90000000E+37"` → `math.inf`.

**Contract:** Convert using Python's `float(text)` rules, which allow surrounding whitespace. If the converted value equals positive `9.9e37`, return `math.inf`, Python's positive infinity value (available after `import math`). Thus both `"9.9E+37"` and `"+9.90000000E+37"` indicate overload. Otherwise return the converted value unchanged. Raise `ValueError` for empty text, whitespace alone, or anything `float()` rejects, such as `"READY"` or `"12 V"`.

**Watch out:** Compare the numeric value, not one exact spelling of the reply. This is an equality check, not a threshold: `"1E+38"` and `"-9.9E+37"` remain their numeric values. No custom number grammar is needed; other special spellings accepted by `float()`, such as `"inf"` and `"nan"` (not a number), keep their usual Python meaning.

**Reread:** [Python Tutorial §3.1.1, Numbers](https://docs.python.org/3/tutorial/introduction.html#numbers) for integers and floating-point numbers; [§3.1.2, Text](https://docs.python.org/3/tutorial/introduction.html#text) for escaped line endings.

### E3 — Prepare the power supply command (easy, ~7 min)

**Goal:** Format a **setpoint**, the value an operator asks the power supply to produce. Here it is measured in **volts**, a unit of electrical voltage. `VOLT` is the instrument's voltage command.

**Signature:** `def format_setpoint(volts: float) -> str`

**Examples:** `5.0` → `"VOLT 5.000"`; `12.3456` → `"VOLT 12.346"`; `0.0` → `"VOLT 0.000"`; `30.0` → `"VOLT 30.000"`.

**Contract:** Accept **finite** values (ordinary numbers rather than infinity or not-a-number) from 0 through 30, including both endpoints. Return uppercase `VOLT`, one space, and the value rounded using Python's **fixed-point format** `.3f`, ordinary decimal notation with exactly three digits after the decimal point and no newline. Raise `ValueError` for any value outside the interval, positive or negative infinity, or `math.nan`. Check the original value before rounding: `30.0001` is invalid even though it would display as `30.000`.

**Watch out:** Python supports a signed zero; `-0.0` is allowed and formats as `"VOLT -0.000"`. An f-string such as `f"{2.5:.2f}"` produces `"2.50"`; change the number of decimal places for this command.

**Reread:** [Python Tutorial §3.1.1, Numbers](https://docs.python.org/3/tutorial/introduction.html#numbers) for numeric values and [§3.1.2, Text](https://docs.python.org/3/tutorial/introduction.html#text) for strings. The formatting syntax needed here is supplied above.

### E4 — Expand the station's channel selection (medium, ~15 min)

**Goal:** Convert a SCPI channel list into the individual channels to measure. A **channel** is a numbered measurement connection. A **range** such as `4:6` includes every channel from its start through its end.

**Signature:** `def split_channels(text: str) -> list[int]`

**Examples:** `"(@1,3,5)"` → `[1, 3, 5]`; `"(@1:4)"` → `[1, 2, 3, 4]`; `"(@1,4:6)"` → `[1, 4, 5, 6]`.

**Contract:**

- Remove surrounding whitespace, then require the exact opening `(@` and closing `)`. Inside must be one or more comma-separated items.
- Each item is either one positive integer or two positive integers separated by exactly one colon. Numbers use only the digits `0` through `9`; leading zeros are allowed (`007` means 7). Signs, decimal points and other characters are invalid. There is no instrument-specific upper limit in this exercise.
- Allow whitespace around the whole list, around items and around either endpoint of a range. For example, `" \t(@ 1 , 4 : 6 )\r\n"` returns `[1, 4, 5, 6]`. Do not allow whitespace inside a number or between the opening `(` and `@`.
- Expand ranges inclusively. Equal endpoints are allowed (`3:3` gives `[3]`); descending ranges such as `4:1` are invalid. Keep item order and repeated channels: `"(@5,1:3,2)"` gives `[5, 1, 2, 3, 2]`.
- Raise `ValueError` for any malformed list, including `"(@)"`, missing wrappers, empty items, trailing commas, zero, negative numbers, missing range endpoints, extra colons or trailing text. Never return a partial list for invalid input.

**Watch out:** `int()` converts digit text to an integer. Python's `range(start, stop)` leaves out `stop`, so an inclusive range needs `end + 1`. A list's `extend(...)` adds each value from another collection. You may use a loop to process the items; needing help here is useful placement feedback.

**Reread:** [Python Tutorial §3.1.2, Text](https://docs.python.org/3/tutorial/introduction.html#text) for string slicing (selecting a portion of text), [§3.1.3, Lists](https://docs.python.org/3/tutorial/introduction.html#lists) for ordered collections, and [§3.2, First Steps Towards Programming](https://docs.python.org/3/tutorial/introduction.html#first-steps-towards-programming) for loops. The extra conversion and range tools are described above.
