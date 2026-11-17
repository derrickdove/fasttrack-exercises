# p04 — Files, errors and reading tracebacks

**Time:** about 65 minutes (11 exercises) · **Read first:** the p04 Read first page in your tracker. Optional lookup: [Python Tutorial 7.2: Reading and Writing Files](https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files) and [8.1–8.4: Errors and Exceptions](https://docs.python.org/3/tutorial/errors.html) · **You edit:** `starter/filesafe.py`

## What you're building

A **test station** is a computer and equipment used to check hardware.
An **operator** is the person running the station; a **reading** is one measured value.
You will read station notes, save short logs, and handle a few expected failures.
You need no equipment and no files prepared by hand.
This prepares you for [d04: files, CSV and JSON](../d04/README.md) and [d05: exceptions](../d05/README.md).
Those sets add tables of measurements and instrument failures after these small steps.

## How this works

1. Open `sets/p04/starter/filesafe.py` in VS Code. Replace each `raise NotImplementedError(...)` body as you reach it. Leave the function names and tests alone. **NotImplementedError** marks unfinished work.
2. Save, then run this command in the Bash terminal from the repository folder:

   ```bash
   bash tools/run.sh p04
   ```

   Type only the command, without a `>>>` prompt. Python examples below belong in a Python file or Python's interactive shell, not at the Bash prompt.
3. At first, expect `Exercises: 0 / 11 passed`. Rerun after each exercise. A **test** checks a result; **pytest** is the tool running these tests. Its **tmp_path** provides a fresh temporary folder for each file test; the tests create all needed files.
4. Report **all pass / partial / stuck** in your tracker. If you reach 65 minutes, report where you got to.

A **function** is named code you call; its **signature** states its name, inputs and result type.
`def` starts a function definition; `()` holds inputs, and commas separate inputs or items.
**Type hints** describe values: `str` means text, `int` a whole number, `float` a number that can have a fractional part, and `bool` either `True` or `False`.
In a signature, `:` introduces an input's type and `->` introduces the result type.
A colon at the end of `def`, `if`, `for`, `with`, `try`, or `except` starts an indented block.
**Indentation** means the leading spaces that group code; use four spaces per level.
`return` sends a value back to the caller; `print()` only displays it.
`None` means no result; a function with no `return` also returns `None`.
`float | None` allows either type; `-> None` says the function has no result to use.

A **list** is an ordered collection: `[]` is empty, and `["a", "b"]` has two items.
`list[str]` describes a list of strings; `parts[0]` selects the first item, counting from zero.
A **dictionary** stores values under keys: `{"bench": "A"}` pairs the key `"bench"` with the value `"A"`.
`dict[str, int]` describes text keys with whole-number values; `counts["good"]` looks up a key.
Keep matching brackets together: `[]`, `{}`, and `()` each close with their own kind.
Quotes enclose text, `\n` means a newline, and `#` starts a comment that Python does not run.
`=` assigns a value; `==` compares for equality and `!=` means not equal.
`<` means less than, `>` means greater than, and `+` adds numbers or joins strings.
`total += 1` means `total = total + 1`; `len(items)` counts items.
`if` runs a block when its condition is true; `else` handles the other case.
`for item in items:` repeats a block for each item in order.
A dot accesses a tool or value belonging to something, as in `line.strip()`.

A **path** is the address of a file or folder; these functions take it as a string.
**UTF-8** is the rule used here to store text characters in files.
All file text uses UTF-8, except the deliberately damaged file tested in E7.
Inputs have the stated types. Numeric readings are ordinary finite numbers; there are no special numeric cases.
Return results without printing. E3 changes a file and returns `None`.

Worked examples solve different tasks. You can run each Python block on its own.
In the file examples, `from tempfile import TemporaryDirectory` brings in Python's temporary-folder tool.
`with TemporaryDirectory() as folder:` creates a disposable folder and removes it afterward.
The lines that write sample text are setup; you will practise writing in E3.

## Exercises

### E1 — Read the operator's note (~5 min)

**Goal:** Read the whole note left by the previous operator. Keep its spaces and newlines.

**New idea:** `open(path, "r", encoding="utf-8")` opens a text file for reading; `"r"` is the read mode. `with ... as source:` gives the opened file a name and closes it when the block ends, even after a failure. `source.read()` returns all the text as one string. Here a visitor-badge example reads a different kind of file:

```python
from tempfile import TemporaryDirectory
with TemporaryDirectory() as folder:
    filename = folder + "/badge.txt"
    with open(filename, "w", encoding="utf-8") as output:
        output.write("Visitor badge\n")
    with open(filename, "r", encoding="utf-8") as source:
        badge = source.read()
    print(len(badge))  # 14
```

**Signature:** `def read_note(path: str) -> str:`

**Examples:** The tests supply these files; you do not create them.

- If `note.txt` contains `"Ready\nCheck cable\n"`, `read_note("note.txt")` returns `"Ready\nCheck cable\n"`.
- If `empty.txt` contains no text, `read_note("empty.txt")` returns `""`.

**Contract:** The file exists. Use `with open(...)` and return its whole text without stripping it.

**If you're stuck:**
1. Reading the whole file needs one string, not a list of lines.
2. Inside `with open(path, "r", encoding="utf-8") as source:`, use `source.read()` and return its result.

### E2 — Collect nonblank log lines (~6 min)

**Goal:** Collect the operator's nonblank log lines in their original order.

**New idea:** A file can be used in `for line in source:` to read one line at a time. `line.strip()` removes spaces and the newline from the two ends; a blank line becomes `""`. `items.append(value)` adds one item to the end of a list. This example cleans party guest names instead of a station log:

```python
guests = [" Jo\n", "\n", "Sam \n"]
names = []
for guest in guests:
    name = guest.strip()
    if name != "":
        names.append(name)
print(names)  # ['Jo', 'Sam']
```

**Signature:** `def clean_lines(path: str) -> list[str]:`

**Examples:**

- A file with `"  CH1 ready  \n\n CH2 ready\n"`: `clean_lines("log.txt")` returns `["CH1 ready", "CH2 ready"]`.
- An empty file: `clean_lines("empty.txt")` returns `[]`.
- A file with `"5.0\n5.0"`: `clean_lines("repeat.txt")` returns `["5.0", "5.0"]`.

**Contract:** The file exists. Strip each line, skip blank results, and return the rest in order, including repeats.

**If you're stuck:**
1. Start with an empty result list; decide whether to add each cleaned line.
2. Use `for line in source:`, then `.strip()`, then `if clean != "":` before `.append(clean)`.

### E3 — Save the operator's checklist (~6 min)

**Goal:** Save a short checklist so the next operator can read one item per line.

**New idea:** `"w"` is the write mode: it creates a file or replaces its old contents. `output.write(text)` writes exactly that text; it does not add a newline for you. Join `"\n"` to each line before writing it. This example saves a shopping item and then reads the saved text:

```python
from tempfile import TemporaryDirectory
with TemporaryDirectory() as folder:
    filename = folder + "/shopping.txt"
    with open(filename, "w", encoding="utf-8") as output:
        output.write("bread" + "\n")
    with open(filename, "r", encoding="utf-8") as source:
        saved = source.read()
    print(saved == "bread\n")  # True
```

**Signature:** `def write_lines(path: str, lines: list[str]) -> None:`

**Examples:**

- `write_lines("check.txt", ["Connect meter", "Start run"])` returns `None`; the file contains `"Connect meter\nStart run\n"`.
- `write_lines("check.txt", ["Stop run"])` returns `None`; it replaces the old text with `"Stop run\n"`.
- `write_lines("check.txt", [])` returns `None`; the file is empty.

**Contract:** The containing folder exists, and supplied lines are nonempty strings without newlines. Replace the file with each line followed by one newline; an empty list produces an empty file. Leave the input list unchanged and return `None`.

**If you're stuck:**
1. Open the output once, then visit each supplied line.
2. Use `with open(path, "w", encoding="utf-8") as output:` and a `for` loop containing `.write(line + "\n")`.

### E4 — Read a table of measurements (~5 min)

**Goal:** Read the station's small measurement table. Give the operator one dictionary per data row.

**New idea:** **CSV** is table text with comma-separated columns; a **header row** names those columns. `import csv` brings in Python's CSV tools, and `csv.DictReader(source)` uses the header names as dictionary keys for each later row. Every value arrives as text, even a value that looks like a number. Open the file with `newline=""` so the CSV tool handles line endings; `list(reader)` collects its row dictionaries into a list, or you can collect them with a loop and `.append(...)`.

```python
import csv
from tempfile import TemporaryDirectory
with TemporaryDirectory() as folder:
    filename = folder + "/books.csv"
    with open(filename, "w", encoding="utf-8", newline="") as output:
        output.write("title,copies,shelf\nAtlas,2,A1\n")
    with open(filename, "r", encoding="utf-8", newline="") as source:
        print(list(csv.DictReader(source)))  # [{'title': 'Atlas', 'copies': '2', 'shelf': 'A1'}]
```

**Signature:** `def read_csv(path: str) -> list[dict[str, str]]:`

**Examples:**

- A file with `"channel,voltage\nCH1,2.5\nCH2,0\n"`: `read_csv("readings.csv")` returns `[{"channel": "CH1", "voltage": "2.5"}, {"channel": "CH2", "voltage": "0"}]`.
- A file with only `"channel,voltage\n"`: `read_csv("empty.csv")` returns `[]`.
- A file with `"operator,status\nLee,ready\n"`: `read_csv("status.csv")` returns `[{"operator": "Lee", "status": "ready"}]`.

**Contract:** The file exists and has a header row with distinct names. Each later row has one value per header; keep every value as text. Return the row dictionaries in file order; a header with no data rows gives `[]`.

**If you're stuck:**
1. The header supplies the keys; do not add it as a data row.
2. Use `with open(path, "r", encoding="utf-8", newline="") as source:`, then collect rows from `csv.DictReader(source)`.

### E5 — Try a numeric reading (~5 min)

**Goal:** Convert an instrument's text to a number. Return `None` when the text is not numeric.

**New idea:** An **exception** is Python's report that an operation failed. **ValueError** is the exception for an unacceptable value, such as text that `float()` cannot convert. A `try` block attempts an operation; `except ValueError:` runs only if that exception happens. Here a ticket counter recovers from invalid whole-number text:

```python
ticket_text = "sold out"
try:
    tickets = int(ticket_text)  # int() converts whole-number text
except ValueError:
    tickets = 0
print(tickets)  # 0
```

**Signature:** `def try_reading(text: str) -> float | None:`

**Examples:** `try_reading("2.5")` returns `2.5`; `try_reading("0")` returns `0.0`; `try_reading("READY")` returns `None`.

**Contract:** Return `float(text)` when conversion works. Catch `ValueError` and return `None` when conversion fails, including for empty text.

**If you're stuck:**
1. Keep the successful result and the failed conversion in separate blocks.
2. Put `float(text)` under `try:` and use `except ValueError:` for the `None` result.

### E6 — Reject an invalid channel (~5 min)

**Goal:** A **channel** is a numbered instrument connection. Reject a channel below one, and tell the operator which value was bad.

**New idea:** `raise ValueError(message)` stops the function and reports an invalid value to its caller. An **f-string** is text starting with `f` that inserts a value inside `{}`. Put the bad value in the message so someone can find the problem. This different example checks a ticket quantity:

```python
def require_tickets(quantity: int) -> int:
    if quantity < 1:
        raise ValueError(f"Bad ticket quantity: {quantity}")
    return quantity
print(require_tickets(3))  # 3
```

**Signature:** `def require_channel(channel: int) -> int:`

**Examples:** `require_channel(1)` returns `1`; `require_channel(8)` returns `8`; `require_channel(-2)` raises `ValueError` with `"-2"` in its message.

**Contract:** Return the supplied channel when it is at least one. Otherwise raise `ValueError` with a message containing the supplied value; the other words are your choice.

**If you're stuck:**
1. Check the bad case before returning a valid channel.
2. Use `if channel < 1:` and an f-string containing `{channel}` in `raise ValueError(...)`.

### E7 — Allow a missing optional log (~6 min)

**Goal:** An optional operator log may not exist yet. Treat that one failure as an empty log.

**New idea:** **FileNotFoundError** is the exception for a missing file. Catching one named exception lets other errors reach the caller. You can call your E2 function inside `try`; you do not need to write its file loop again. This example handles **KeyError**, the exception for a missing dictionary key, instead:

```python
seats = {"Jo": "A1"}
try:
    seat = seats["Sam"]
except KeyError:  # KeyError means the dictionary key is missing
    seat = "unassigned"
print(seat)  # unassigned
```

**Signature:** `def optional_lines(path: str) -> list[str]:`

**Examples:**

- A file with `" CH1 \n\nCH2\n"`: `optional_lines("log.txt")` returns `["CH1", "CH2"]`.
- If no such file exists, `optional_lines("missing.txt")` returns `[]`.
- If `damaged.txt` is not UTF-8 text, `optional_lines("damaged.txt")` still raises **UnicodeDecodeError**, Python's error for unreadable text encoding.

**Contract:** Return the same result as `clean_lines(path)` for a readable file. Return `[]` for `FileNotFoundError` only; all other exceptions must reach the caller. Do not create or change any file.

**If you're stuck:**
1. A missing optional file is expected; a damaged file should still be reported. You need no code to repair damaged text.
2. Call `clean_lines(path)` inside `try:` and catch only `except FileNotFoundError:`.

### E8 — Turn labels into JSON and back (~6 min)

**Goal:** Turn the station's text labels into text another program can read, then recover the labels.

**New idea:** **JSON** is a text format for exchanging structured data, such as a dictionary. `import json` makes Python's JSON tools available; `json.dumps(data)` returns JSON text and `json.loads(text)` reads it back into Python values. The `s` in both names means they work with strings; no file is needed. This example exchanges a pet's details:

```python
import json
pet = {"name": "Milo", "kind": "cat"}
text = json.dumps(pet)
restored = json.loads(text)
print(restored == pet)  # True
```

**Signature:**

```python
def labels_to_json(labels: dict[str, str]) -> str:
def labels_from_json(text: str) -> dict[str, str]:
```

**Examples:**

- `labels_to_json({"bench": "B2"})` returns `'{"bench": "B2"}'`.
- `labels_from_json('{"operator": "Lee"}')` returns `{"operator": "Lee"}`.
- `labels_from_json(labels_to_json({}))` returns `{}`.

**Contract:** All dictionaries have only string keys and string values, and input JSON always describes such a dictionary. Return JSON text from the first function and the recovered dictionary from the second; spacing and key order in the JSON text are your choice. Do not read or write files.

**If you're stuck:**
1. Encoding goes from a Python dictionary to text; decoding goes back the other way.
2. Use `json.dumps(...)` and `json.loads(...)`; you can name the decoded result with `labels: dict[str, str] = ...` before returning it, just as type hints describe function inputs.

In [d04](../d04/README.md), `json.dump` writes to an open file, while `json.dumps` gives you text. That set also creates folders with `Path.mkdir(parents=True, exist_ok=True)`.

### E9 — Ask a path about a file (~5 min)

**Goal:** Show the operator a log file's name, its ending, and whether it exists.

**New idea:** **pathlib** is Python's module for working with paths; `from pathlib import Path` brings in its `Path` tool. For a path object, `.name` is the final name and `.suffix` is the last file ending, including its dot. `.exists()` returns `True` or `False` without opening the file. This example describes a picture that need not exist:

```python
from pathlib import Path
picture = Path("album") / "dog.png"  # / joins path parts here
print(picture.name)    # dog.png
print(picture.suffix)  # .png
```

**Signature:** `def file_details(path: str) -> dict[str, str | bool]:`

`str | bool` allows either text or a boolean as a dictionary value.

**Examples:**

- If the file exists, `file_details("logs/run.txt")` returns `{"name": "run.txt", "suffix": ".txt", "exists": True}`.
- If it is missing, `file_details("logs/missing.json")` returns `{"name": "missing.json", "suffix": ".json", "exists": False}`.
- If the file exists, `file_details("README")` returns `{"name": "README", "suffix": "", "exists": True}`.

**Contract:** Paths name existing or missing files, not folders. Return exactly the keys `"name"`, `"suffix"`, and `"exists"`; no opening or creating files is needed. Do not create or change any file.

**If you're stuck:**
1. Make one `Path` object and ask it for the three pieces of information.
2. Use `Path(path)`, then `.name`, `.suffix`, and `.exists()`; only the last needs parentheses.

### E10 — Count good and bad readings (~8 min)

**Goal:** Summarize a station log containing one reading per nonblank line. Count numeric lines as good and other nonblank lines as bad.

**New idea:** Combine the cleaned lines from E2 with the conversion from E5 and two counters. Use `value is None` to ask whether conversion failed; `0.0` is still a good reading. You may call your earlier functions here. This example counts accepted and declined invitations:

```python
counts = {"yes": 0, "no": 0}
for reply in ["yes", "no", "yes"]:
    if reply == "yes":
        counts["yes"] += 1
    else:
        counts["no"] += 1
print(counts)  # {'yes': 2, 'no': 1}
```

**Signature:** `def count_readings(path: str) -> dict[str, int]:`

**Examples:**

- A file with `"2.5\nREADY\n0\n\n"`: `count_readings("run.txt")` returns `{"good": 2, "bad": 1}`.
- An empty file: `count_readings("empty.txt")` returns `{"good": 0, "bad": 0}`.
- A file with `"ERROR\nWAIT\n"`: `count_readings("bad.txt")` returns `{"good": 0, "bad": 2}`.

**Contract:** The file exists; strip lines and ignore blank lines. Return exactly the keys `"good"` and `"bad"`, counting every remaining line once, including repeats.

**If you're stuck:**
1. Begin both counters at zero; each nonblank line increases exactly one counter.
2. Loop over `clean_lines(path)`, pass each line to `try_reading`, and branch with `if value is None:`.

### E11 — Read three failures (QUIZ, ~8 min)

**Goal:** Help an operator find the failed line and choose a useful repair. Return your choices as question ids paired with uppercase option letters, as in the other quiz sets.

**New idea:** A **traceback** lists the calls that led to a failure; its last line gives the exception type and message. Read that LAST line first, then find the innermost file and line number above it. **TypeError** means an operation received an unsuitable type; the repair may be in a helper that produced that value. For this different recipe problem, read `KeyError: 'beans'`, find `recipe.py`, line 2, and change the lookup to the existing key `"rice"`:

```text
Traceback (most recent call last):
  File "/kitchen/recipe.py", line 2, in <module>
    amount = grams["beans"]
KeyError: 'beans'
```

```python
grams = {"rice": 50}
amount = grams["rice"]
print(amount)  # 50
```

**Signature:** `def traceback_answers() -> dict[str, str]:`

**Examples:** `sorted(traceback_answers())` returns `["Q1", "Q2", "Q3"]` (`sorted` puts the keys in order); `len(traceback_answers())` returns `3`. These calls show the shape without supplying the correct letters.

Each question below has one correct choice. Each option names the file and line, the error, and what to change. These are full tracebacks from small scripts; your test runner normally prints a shorter report.

**Q1.** `run_check.py` calls `enough(readings)` from `checks.py`. Inside `enough`, `readings` is a list of readings, and the station wants to know whether it has more than two readings.

```text
Traceback (most recent call last):
  File "/station/run_check.py", line 4, in <module>
    ready = enough([1.0, 2.0, 3.0])
  File "/station/checks.py", line 2, in enough
    return readings > 2
TypeError: '>' not supported between instances of 'list' and 'int'
```

- A. `run_check.py`, line 4; `ValueError`; change the reading values to strings.
- B. `checks.py`, line 2; `TypeError`; compare `len(readings)` with `2`.
- C. `checks.py`, line 2; `TypeError`; replace `>` with `=` to compare the count.

**Q2.** The helper in `readback.py` is:

```python
def read_voltage():
    print(2.5)
```

The terminal first displays `2.5`, then this full traceback:

```text
Traceback (most recent call last):
  File "/station/run_total.py", line 3, in <module>
    total = read_voltage() + 1.0
TypeError: unsupported operand type(s) for +: 'NoneType' and 'float'
```

- A. Failure at `run_total.py`, line 3; `TypeError`; call `print(read_voltage())` to obtain a number.
- B. Failure at `run_total.py`, line 3; `ValueError`; change `1.0` to `"1.0"`.
- C. Failure at `run_total.py`, line 3; `TypeError`; change `readback.py`, line 2, to return the reading instead of printing it.

**Q3.** `readback.py` contains `def numeric(text):` on line 1 and the conversion below on line 2. The operator's log can contain status words; the desired result for a status word is `None`.

```text
Traceback (most recent call last):
  File "/station/run_parse.py", line 3, in <module>
    voltage = numeric("READY")
  File "/station/readback.py", line 2, in numeric
    return float(text)
ValueError: could not convert string to float: 'READY'
```

- A. `readback.py`, line 2; `ValueError`; handle conversion with `try` / `except ValueError` and return `None` on failure.
- B. `run_parse.py`, line 3; `FileNotFoundError`; create a file called `READY`.
- C. `readback.py`, line 2; `ValueError`; use `print(text)` to return a numeric reading.

**Contract:** Return exactly `"Q1"`, `"Q2"`, and `"Q3"` as keys, each with one uppercase letter: `"A"`, `"B"`, or `"C"`. Return letters, not the option text; you do not edit or run the broken scripts. Quiz failures point to the idea to revisit without revealing the correct letter.

**If you're stuck:**
1. Read the last line, then the last file/line entry; ask what type each value really has.
2. Revisit `len(...)` in How this works for Q1, `return` versus `print` for Q2, and E5's `except ValueError:` for Q3; return a dictionary literal with your choices.

In [d05](../d05/README.md), you also use `str.partition` and return a tuple; both are explained in that set's README.
