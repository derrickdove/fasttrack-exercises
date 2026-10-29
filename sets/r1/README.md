# r1 — Week 1 review: weekly review, block 1

**Time:** about 50 minutes · **Read first:** review day, no new reading; reuse the d01–d06 readings listed below · **You edit:** `starter/review1.py`

## What you're building

A chassis test station checks electrical connections and records measurements for an operator. You will read the station's instrument list, load measurements with their limits, and write a small report showing how many checks passed. A bad input row must give the operator a useful message and preserve the previous report.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/review1.py`. Don't edit `tests/`. The two dataclasses and the enum are supplied; leave their declarations in place.
2. Press **Ctrl+Shift+B → Test: r1** (or run `bash tools/run.sh r1` / `tools\run.ps1 r1` from the repository root). At first you'll see `Exercises: 0 / 5 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker. Note which earlier topic needs more practice.

Earlier readings, by name:

- **d01:** Python Tutorial §3 (numbers and strings).
- **d02:** Python Tutorial §4.1–4.8 (decisions, loops, functions).
- **d03:** Python Tutorial §5 (data structures); *A Common-Sense Guide to DSA*, chapter on hash tables.
- **d04:** Python Tutorial §7.2 (files); `csv`, `json`, `pathlib` documentation; *Automate the Boring Stuff*, chapter on CSV and JSON.
- **d05:** Python Tutorial §8 (errors and exceptions); *The Pragmatic Programmer*, “Dead Programs Tell No Lies”.
- **d06:** Python Tutorial §9 (classes); `dataclasses` and `enum` documentation.

A **dataclass** is a class whose named fields get an automatically generated constructor and equality comparison; `frozen=True` prevents changing fields after construction.
An **enum** gives names to fixed choices: return `Status.PASS`, for example, rather than the string `"PASS"`.
An **exception** reports a failure; a subclass such as `RowError(ValueError)` can be caught as either type.
A **channel** is the name of a measurement point, such as `BUS`; a **limit** is the allowed lower or upper value.
**CSV** is a table stored as comma-separated text; **JSON** is a text format for values such as dictionaries and lists.
`Path` represents a file or folder location; **UTF-8** is the text encoding used for every file here.
`float | None` means either a number or `None`, which here means there is no bound on that side.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Station:
    name: str
print(Station("bench-2").name)  # bench-2
```

All paths passed to your functions are `pathlib.Path` objects. File read/write errors, including `FileNotFoundError` for a missing input, propagate to the caller: do not replace them with empty results. No function prints anything. Do the exercises in order; E3 uses E2, and E5 uses E3 and E4. No imports from another set are needed.

## Exercises

### E1 — Load the station's instrument list (easy, ~9 min)

**Goal:** Read a file of instrument identification replies into the supplied frozen `Instrument` dataclass. `*IDN?` is the identification query in SCPI (Standard Commands for Programmable Instruments); each reply names the manufacturer, model, serial number (the instrument's unique identifier), and firmware (software inside the instrument).

**Signature:** `def read_inventory(path: Path) -> list[Instrument]`

Read UTF-8 text, one reply per physical file line. Skip empty or whitespace-only lines. Split each other line on commas, strip whitespace around each field, and require exactly four nonempty fields. Construct `Instrument(manufacturer, model, serial, firmware)` for each reply. Preserve order, capitalization, and duplicates. An empty or all-blank file returns `[]`. This simple reply format has no quoted fields or commas within fields.

**Example:** a file containing `" Acme , DMM1 , SN7 , 2.0\n"` → `[Instrument("Acme", "DMM1", "SN7", "2.0")]`.

**Watch out:** For an invalid reply on line N, raise `ValueError` with the exact message `"line N: expected four nonempty fields"`. Count file lines from 1, including skipped blank lines. Stop at the first invalid reply. `data/inventory.txt` is a valid example.

**Reread:** d01 — Python Tutorial §3, strings and `split`; d04 — Python Tutorial §7.2 and `pathlib`; d06 — `dataclasses` documentation.

### E2 — Give the operator a row error (easy, ~6 min)

**Goal:** Implement the supplied `RowError` class for problems in the measurement table. A row is one table record; its line number tells the operator where to look in the file.

**Signatures:** `RowError.__init__(self, line_number: int, reason: str) -> None` and `RowError.__str__(self) -> str`

Store the two arguments unchanged in `self.line_number` and `self.reason`. Initialize the base exception with both arguments, so `error.args == (line_number, reason)`. `str(error)` must return `"line <line_number>: <reason>"`. Arguments are already valid; add no validation or trimming.

**Example:** `str(RowError(7, "invalid number"))` → `"line 7: invalid number"`.

**Watch out:** Keep `RowError` a subclass of `ValueError`. Calling `super().__init__(line_number, reason)` initializes the base exception. An empty reason still leaves the space after the colon.

**Reread:** d05 — Python Tutorial §8, user-defined exceptions and “Dead Programs Tell No Lies”; d06 — Python Tutorial §9, methods and inheritance.

### E3 — Read a table with limits (medium, ~14 min)

**Goal:** Load a CSV file into the supplied frozen `Measurement(channel, value, unit, low, high)` dataclass. Limits are **inline**, meaning each row carries the limits for its own measurement. A unit names the quantity's scale: `V` means volts and `A` means amperes.

**Signature:** `def load_measurements(path: Path) -> list[Measurement]`

Open UTF-8 text with `newline=""` and use `csv.reader`. The first physical line must parse into exactly the five header fields `channel,value,unit,low,high` in that order, without spaces around header names. Standard CSV quoting is allowed in the header too. Skip empty or whitespace-only lines after the header. All inputs use valid CSV quoting, and each record fits on one physical line: quoted commas such as `"sense,aux"` are allowed, embedded line breaks are outside this exercise.

For each remaining row, check these rules in this order. On the first failed rule, raise `RowError` with the physical line number (starting at 1, including the header and blank lines) and the exact reason below.

| Check | Reason |
| --- | --- |
| Missing, empty, reordered, or otherwise different header | `bad header` (always line 1) |
| Row does not have exactly five fields | `expected 5 fields` |
| After stripping every field, channel or unit is empty | `empty channel or unit` |
| Value, or a nonempty low/high field, cannot be converted with `float()` | `invalid number` |
| Any converted number is not finite | `non-finite number` |
| Both bounds exist and low is greater than high | `reversed limits` |

**Finite** means a regular number, excluding `nan` (not a number) and positive/negative infinity; use `math.isfinite`. A blank value is an error. Blank low/high cells become `None`; zero is a real bound. Equal limits are valid. Preserve row order, repeated channels, and case. Units need only be nonempty: do not convert or restrict them. Return `[]` for a header-only file. Do not return partial data after a bad row.

**Example:** `BUS,+2.8e1,V,27,29` → `Measurement("BUS", 28.0, "V", 27.0, 29.0)`. `RETURN,0,A,,0` has `low=None` and `high=0.0`. `data/readings.csv` is a valid sample table.

**Watch out:** A line containing only spaces is blank; a line containing commas or quotes is a record and must be checked. For example, `""` and `"   "` each have only one field and must raise `expected 5 fields`. Conversion must succeed for all numeric cells before checking finiteness. `csv.reader.line_num` gives the physical line count, including skipped blank lines.

**Reread:** d04 — `csv` and `pathlib` documentation and the CSV/JSON chapter; d05 — Python Tutorial §8, raising exceptions; d06 — `dataclasses` documentation.

### E4 — Check each reading (easy, ~8 min)

**Goal:** Compare a measurement to its bounds and return one of the supplied `Status` enum members.

**Signature:** `def classify(reading: Measurement) -> Status`

Return `Status.LOW` when a lower bound exists and value is below it; `Status.HIGH` when an upper bound exists and value is above it; otherwise return `Status.PASS`. Bounds are **inclusive**: a value exactly equal to a bound passes. `None` removes only that bound; both `None` means every value passes. Inputs are valid measurements with finite numbers and ordered bounds, as produced by E3. Do not change the measurement or convert its unit; limits and value already share that unit.

**Example:** `classify(Measurement("BUS", 26.9, "V", 27.0, 29.0))` → `Status.LOW`.

**Watch out:** A bound of `0.0` is present. Check for `None` explicitly. Return enum members, not their string values.

**Reread:** d02 — Python Tutorial §4.1–4.8, decisions and functions; d06 — `enum` documentation.

### E5 — Publish the shift summary (medium, ~13 min)

**Goal:** Combine the table loader and classifier to write the operator's JSON report.

**Signature:** `def write_summary(csv_path: Path, json_path: Path) -> dict[str, int]`

Call E3 to read and validate the entire input, and use E4 to check each measurement. Return a dictionary with exactly these four integer counts, and write that same dictionary to the output:

| Key | Count |
| --- | --- |
| `total` | Number of measurement rows |
| `passed` | Rows classified `Status.PASS` |
| `failed` | Rows classified `Status.LOW` or `Status.HIGH` |
| `channels` | Number of distinct channel names after E3's stripping; names are case-sensitive |

Repeated readings still count as separate results. A valid header-only CSV gives zero for all four counts. Create missing parent folders, then replace any existing output with UTF-8 JSON formatted using `indent=2`, `sort_keys=True`, and one trailing newline. Input and output are different paths. Preserve the input CSV.

**Example:** For `data/readings.csv`, return and write `{"total": 4, "passed": 3, "failed": 1, "channels": 3}` (the file's keys are sorted).

**Watch out:** Finish reading and validating before creating output folders or opening the output file. If input loading fails, propagate that exception unchanged and leave any existing report, or absent output folder, untouched. Output write errors also propagate; you do not need special recovery for a write error.

**Reread:** d03 — Python Tutorial §5, sets and dictionaries; d04 — `json` and `pathlib` documentation and the CSV/JSON chapter; d05 — Python Tutorial §8, exception propagation; d06 — `enum` documentation.
