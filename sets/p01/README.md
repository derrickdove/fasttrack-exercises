# p01 — First steps: values, text and your first functions

**Time:** about 61 minutes (12 exercises) · **Read first:** the p01 Read first page in your tracker. Optional lookup: [Automate the Boring Stuff 2e chapter 1](https://automatetheboringstuff.com/2e/chapter1/) and [the def/return part of chapter 3](https://automatetheboringstuff.com/2e/chapter3/) · **You edit:** `starter/basics.py`

## What you're building

A **test station** is a computer and equipment used to check hardware. An **operator** is the person running it. A **reading** is one measured value. A **channel** is a numbered connection on the equipment.

Build small helpers that return station labels and turn simple replies into useful values. This consolidates the pieces you used in d01 with coaching. Each piece gets its own practice here. You need no equipment.

## How this works

1. Open `sets/p01/starter/basics.py`. Replace only the `raise NotImplementedError(...)` line for the current exercise. Keep its `def` line and the line in triple quotes. A **docstring** is the description in triple quotes; a **NotImplementedError** marks unfinished code, and `raise` stops that function with the named error.
2. Save the file. From the repository folder, run `bash tools/run.sh p01` in the VS Code terminal. Start with `Exercises: 0 / 12 passed`. Rerun after each exercise. Several checks can belong to one exercise; they all need to pass. Don't edit `tests/`.
3. Report **all pass / partial / stuck** in the tracker. If an exercise takes longer than its estimate, record where you got stuck and ask your coach for a hint.

A **shell** is a program that runs commands such as `bash tools/run.sh p01`. Write Python in the starter file, not at the shell prompt. The worked examples below are for reading; they are complete Python snippets you can also run in a separate practice file. If you use Python's interactive window, `>>>` is its prompt, not something to type.

A **function** is named code that does a small job. A **signature** is its first line, beginning with `def`. A **call** runs a function by writing its name followed by parentheses `()`; matching parentheses hold any inputs. A colon `:` at the end of a `def` line starts the function body. **Indentation** means spaces at the start of a line; use four spaces for lines inside a function.

A **type hint** describes the expected kind of value: `str` means text, `int` means a whole number, and `float` means a number that can have a fractional part. `->` introduces the return type. A **string** is text between matching quotes, such as `"READY"`; the quotes are not part of the text. A **comment** is a note after `#` that Python ignores.

Inputs in this set have the stated types and are valid. Return results; do not print inside your exercise functions. No input checking or special number cases are needed. Read each worked example, then solve the different task below it.

The 12 exercises total about 61 minutes. The last exercise is a quiz: read the errors and choose answers before editing its function.

For the quiz answer format, a **dictionary** pairs names called **keys** with values: `{}` surrounds the pairs, `:` separates each key from its value, and commas separate pairs. `dict[str, str]` means text keys and text values; a quoted key in square brackets `[]` selects its value.

This small practice example uses different questions and letters:

```python
def practice_answers() -> dict[str, str]:
    return {"P1": "D", "P2": "B"}

print(practice_answers()["P1"])  # D
print(practice_answers()["P2"])  # B
```

In `error_answers()`, return exactly the keys `"Q1"`, `"Q2"` and `"Q3"`, each paired with one chosen uppercase letter `"A"`, `"B"` or `"C"`. Use the dictionary shape above with those three keys and your own letters. Return letters, not the option sentences.

## Exercises

### E1 — Return the station label (easy, ~4 min)

**Goal:** Give the operator's screen a fixed station label.

**New idea:** A **return value** is the result a function sends back to its caller with `return`. `print()` displays something on screen; it does not send that result back. A function that finishes without returning a value returns **None**, Python's value for no result.

```python
def connector_kind() -> str:
    return "USB"

print(connector_kind())  # USB
```

**Signature:** `def station_label() -> str:`

**Examples:**

```python
station_label()  # "STATION READY"
station_label()  # "STATION READY" again: it is a fixed label
```

**Contract:** Return exactly `"STATION READY"` every time. Use uppercase letters and one space, with no extra line ending.

**If you're stuck:**

1. The tests need a value they can receive, not a message on screen.
2. Use a line shaped like `return "some text"` inside the function.

### E2 — Convert millivolts to volts (easy, ~5 min)

**Goal:** Convert a station reading from **millivolts** to **volts**, units of electrical voltage. There are 1,000 millivolts in one volt.

**New idea:** A **parameter** is the name a function uses for an input value. A **variable** is a name holding a value; `=` assigns a value to a name. A colon between a parameter name and its type hint says what kind of input to expect. `/` divides numbers and gives a `float` result.

```python
def centimetres_to_metres(centimetres: float) -> float:
    metres = centimetres / 100
    return metres

print(centimetres_to_metres(250.0))  # 2.5
```

**Signature:** `def millivolts_to_volts(millivolts: float) -> float:`

**Examples:**

```python
millivolts_to_volts(5000.0)  # 5.0
millivolts_to_volts(250.0)   # 0.25
millivolts_to_volts(0.0)     # 0.0
```

**Contract:** Return the millivolt reading divided by 1,000 as a `float`. Do not round it or turn it into text.

**If you're stuck:**

1. One volt is a larger unit, so the number becomes smaller.
2. Use `/` with the parameter and the conversion factor, then return the result.

### E3 — Label a channel reading (easy, ~5 min)

**Goal:** Show the channel number beside a reading that is already in volts.

**New idea:** An **f-string** is text with an `f` before its opening quote that inserts values inside curly braces `{}`. Put the variable name between the braces; Python supplies its value. A comma `,` separates multiple parameters or input values in a call.

```python
def rack_label(rack: int, shelf: int) -> str:
    label = f"Rack {rack}, shelf {shelf}"
    return label

print(rack_label(2, 7))  # Rack 2, shelf 7
```

**Signature:** `def channel_label(channel: int, volts: float) -> str:`

**Examples:**

```python
channel_label(3, 5.0)   # "CH3: 5.0 V"
channel_label(1, 4.98)  # "CH1: 4.98 V"
channel_label(12, 0.0)  # "CH12: 0.0 V"
```

**Contract:** Return `CH`, the channel number, a colon and space, the volts value, then a space and `V`. Use the normal f-string display of the number; no rounding or extra decimal-place rules are needed. The colon inside the output is ordinary text.

**If you're stuck:**

1. Keep the fixed parts outside the braces and put changing values inside them.
2. Start the returned text with `f"` and use one pair of braces for each parameter.

### E4 — Clean an operator entry (easy, ~5 min)

**Goal:** Make an operator's entry consistent before showing it on the station screen.

**New idea:** A **method** is an operation called on a value using a dot `.` and its name. The string method `strip()` removes spaces and line endings at the two ends. `upper()` changes letters to uppercase; each method returns new text that you can store or return.

```python
def tidy_colour(colour: str) -> str:
    trimmed = colour.strip()
    loud = trimmed.upper()
    return loud

print(tidy_colour("  blue  "))  # BLUE
```

**Signature:** `def clean_operator(entry: str) -> str:`

**Examples:**

```python
clean_operator("  sam  ")  # "SAM"
clean_operator("Lee")      # "LEE"
clean_operator(" ann wu ") # "ANN WU"
```

**Contract:** Strip the entry's ends, then return its uppercase version. Preserve spaces between words.

**If you're stuck:**

1. Calling a string method does not change the original variable's text.
2. Store the result of `entry.strip()`, then call `upper()` on that result.

### E5 — Count a serial number's characters (easy, ~4 min)

**Goal:** Tell an operator how long a **serial number** is, the text identifying one hardware unit.

**New idea:** `len()` returns the number of characters in a string as an `int`. Every character counts, including a digit. The result is a number, not text.

```python
def label_length(label: str) -> int:
    size = len(label)
    return size

print(label_length("METER"))  # 5
```

**Signature:** `def serial_length(serial: str) -> int:`

**Examples:**

```python
serial_length("AB12")  # 4
serial_length("K7")    # 2
```

**Contract:** Serial numbers are nonempty text made of letters and digits. Return their character count as an integer. Do not convert the serial number to a number.

**If you're stuck:**

1. Count all the characters, including the digits.
2. Call `len(...)` with the serial number, then return the count.

### E6 — Inspect a serial number (easy, ~4 min)

**Goal:** Help an operator check a serial number. Write two tiny helpers for its first character and last character.

**New idea:** An **index** is a character's position, starting at zero; square brackets `[]` select that character. Index `-1` means the last character, with the minus sign counting back from the end. Both forms select one character; neither counts the characters.

```python
word = "METER"
first = word[0]
last = word[-1]
print(first)  # M
print(last)   # R
```

**Signature:**

```python
def first_character(serial: str) -> str:
def last_character(serial: str) -> str:
```

**Examples:** For the first-character helper:

```python
first_character("AB12")  # "A"
first_character("K7")    # "K"
```

For the last-character helper:

```python
last_character("AB12")  # "2"
last_character("K7")    # "7"
```

**Contract:** Serial numbers are nonempty text made of letters and digits. Return a one-character string from each helper. Treat digits as characters here; do not convert them to numbers.

**If you're stuck:**

1. The first position is zero; a negative position counts from the end.
2. Use `[0]` in the first helper and `[-1]` in the last helper.

### E7 — Take a model prefix (easy, ~4 min)

**Goal:** Get the three-character family label at the start of an instrument's model name. An **instrument** is equipment that measures or controls something.

**New idea:** A **slice** selects a piece of text with `[start:stop]`. The stop position is left out. Leaving out `start` means start at the beginning.

```python
def two_letter_region(code: str) -> str:
    region = code[:2]
    return region

print(two_letter_region("UK-LAB"))  # UK
```

**Signature:** `def model_prefix(model: str) -> str:`

**Examples:**

```python
model_prefix("DMM6500")  # "DMM"
model_prefix("PSU300")   # "PSU"
model_prefix("ABC")      # "ABC"
```

**Contract:** Model names have at least three characters. Return exactly their first three characters, keeping their original capitalization.

**If you're stuck:**

1. Positions zero, one and two are the first three characters.
2. Use a slice with its start omitted and its stop just after the wanted characters.

### E8 — Pick the reading field (easy, ~5 min)

**Goal:** Pick out just the reading text from a comma-separated instrument reply.

**New idea:** A **field** is one part of text separated from the next by a chosen character. `split(separator)` breaks a string into a **list**, an ordered collection of values. Use the indexing from E6 to select one item; the first item is still at position zero.

```python
reply = "rack7;READY;operator2"
parts = reply.split(";")
state = parts[1]
print(parts)  # ['rack7', 'READY', 'operator2']
print(state)  # READY
```

**Signature:** `def reading_field(reply: str) -> str:`

**Examples:**

```python
reading_field("CH3,4.98,V")  # "4.98"
reading_field("CH1,0.0,V")   # "0.0"
reading_field("CH12,12.5,V") # "12.5"
```

**Contract:** Every reply has exactly three comma-separated fields: channel, reading and unit, with no spaces or line ending. Return the second field as text. Do not convert it to a number yet.

**If you're stuck:**

1. Splitting finds the field boundaries; indexing picks one field.
2. Call `reply.split(",")`, then select the second item with a zero-based index.

### E9 — Turn numeric text into numbers (easy, ~6 min)

**Goal:** Turn a typed channel number and a typed voltage into values the station can calculate with. Write one helper for each kind of number.

**New idea:** A **conversion** changes a value from one type to another. `int(text)` converts whole-number text to an integer. `float(text)` converts numeric text to a number that can have a fractional part. Quotes make `"18"` text; converting it gives the number `18`.

```python
count_text = "18"
duration_text = "0.25"
count = int(count_text)
duration = float(duration_text)
print(count)     # 18
print(duration)  # 0.25
```

**Signature:**

```python
def parse_channel(text: str) -> int:
def parse_voltage(text: str) -> float:
```

**Examples:** For the whole-number helper:

```python
parse_channel("3")   # 3
parse_channel("12")  # 12
```

For the voltage helper:

```python
parse_voltage("4.98")  # 4.98
parse_voltage("5")     # 5.0
```

**Contract:** Channel text contains a positive whole number; voltage text contains an ordinary decimal number, with or without a decimal point. Inputs contain no units, spaces or line endings. Return an `int` from `parse_channel` and a `float` from `parse_voltage`.

**If you're stuck:**

1. Removing quotes by hand is not the job; the function receives a text value and converts it.
2. Return a call to `int(...)` in one helper and `float(...)` in the other.

### E10 — Read a complete reply (combine, ~7 min)

**Goal:** Read the voltage from an instrument reply with a channel, an equals sign and a trailing line ending.

**New idea:** There is no new Python tool here: combine cleaning, splitting, indexing and conversion. A **newline** ends a line; Python writes it as `\n` inside a string, where the backslash introduces that special character. The `=` inside this reply's quotes is an ordinary separator, not a Python assignment.

```python
reply = "seconds:2.5\n"
cleaned = reply.strip()
parts = cleaned.split(":")
duration = float(parts[1])
print(duration)  # 2.5
```

**Signature:** `def reading_value(reply: str) -> float:`

**Examples:**

```python
reading_value("CH3=4.98\n")  # 4.98
reading_value("CH1=0.0\n")   # 0.0
reading_value("CH12=5\n")    # 5.0
```

**Contract:** Every reply is a channel name, one `=`, ordinary decimal reading text and one trailing `\n`, with no spaces. Return the reading as a `float`. Do not return the channel or the newline.

**If you're stuck:**

1. Make each small step produce a value for the next step.
2. Try separate lines using `strip()`, `split("=")`, an index and `float()`.

### E11 — Report a millivolt reading (combine, ~6 min)

**Goal:** Give the operator one status line for a channel whose reading arrives in millivolts. Display the reading in volts.

**New idea:** There is no new syntax: do the arithmetic first, then insert the result into text. Keep units clear by giving the converted value a useful name. You may call your E2 and E3 helpers, or do the same steps inside this function.

```python
def travel_label(route: int, centimetres: float) -> str:
    metres = centimetres / 100
    return f"Route {route}: {metres} m"

print(travel_label(4, 350.0))  # Route 4: 3.5 m
```

**Signature:** `def status_message(channel: int, millivolts: float) -> str:`

**Examples:**

```python
status_message(3, 4980.0)  # "CH3: 4.98 V"
status_message(1, 5000.0)  # "CH1: 5.0 V"
status_message(12, 0.0)    # "CH12: 0.0 V"
```

**Contract:** Convert the millivolt input to volts by dividing by 1,000. Return the same text layout as E3: `CH`, the channel, a colon and space, the converted number, a space and `V`. Use normal f-string number display with no rounding and no newline.

**If you're stuck:**

1. You already know how to convert this unit and how to label a channel.
2. Store the numeric conversion from E2 before building the f-string from E3.

### E12 — Read the error message (QUIZ, easy, ~6 min)

**Goal:** Help an operator understand why three tiny station snippets stop. Choose the cause of each error; do not put the broken snippets into your starter file.

**New idea:** An **error message** tells you why Python stopped; read its last line first. A **NameError** means a name was not found, a **TypeError** means an operation cannot use those types together, and an **IndentationError** means leading spaces do not form a valid block.

```python
instrument = "SCOPE"
# If Python reports: NameError: name 'instument' is not defined
# Compare that name with the assignment above, then correct it:
print(instrument)  # SCOPE
```

**Signature:** `def error_answers() -> dict[str, str]:`

**Examples:** These calls check your quiz result without revealing the correct choices:

```python
len(error_answers())        # 3 entries
len(error_answers()["Q1"])  # 1 character in the chosen letter
```

For this quiz, `+` adds two numbers or joins two strings; it cannot directly join a string and a number. A function's body needs indentation even if it has only one line.

**Q1.** An operator runs this snippet:

```python
volts = 5.0
print(vlots)
```

```text
NameError: name 'vlots' is not defined
```

- A. The variable name was misspelled when it was used.
- B. `print()` can only display text, never numbers.
- C. The number needs quotation marks before it can be stored.

**Q2.** A channel label fails:

```python
channel = 3
print("CH" + channel)
```

```text
TypeError: can only concatenate str (not "int") to str
```

Here, **concatenate** means join text together.

- A. A channel number cannot be stored in a variable.
- B. The text label should be lowercase.
- C. `+` was asked to join text and a whole number directly.

**Q3.** A station helper fails before it can run:

```python
def ready_label() -> str:
return "READY"
```

```text
IndentationError: expected an indented block after function definition
```

- A. A function cannot return text.
- B. The `return` line needs four leading spaces to be inside the function.
- C. The function needs an input parameter.

**Contract:** Choose one answer for each question using the format in How this works. Answer by reading; do not run the broken snippets inside your function.

**If you're stuck:**

1. Match each final error line to the name, types or indentation in the lines above it.
2. For `TypeError`, check the two values on either side of `+`.

After this set, continue with p02, then d02. d01, the placement check you did first, needs decisions and rejecting bad input; those come in p02. Revisit d01 later on a review day.
