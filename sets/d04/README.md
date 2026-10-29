# d04 — Logs in, results out: files, CSV and JSON

**Time:** about 45 minutes · **Read first:** [Python Tutorial §7.2: Reading and Writing Files](https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files), the [`csv`](https://docs.python.org/3/library/csv.html), [`json`](https://docs.python.org/3/library/json.html) and [`pathlib`](https://docs.python.org/3/library/pathlib.html) docs; *Automate the Boring Stuff*, Working with CSV Files and JSON Data; [Pro Git 2.1–2.2: Getting a Git Repository and Recording Changes to the Repository](https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository) · **You edit:** `starter/logs.py`

## What you're building

A test station is a computer connected to instruments that measure hardware. Its operator needs to read measurement logs, save results and combine logs from several runs. You will build four file functions that turn recorded instrument readings into useful output.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/logs.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d04** (or run `bash tools/run.sh d04` / `tools\run.ps1 d04` from the repository root). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A **path** locates a file or folder. `pathlib.Path` represents it without choosing Windows or Linux separators. A **parent** is the folder containing a path; `parents=True` creates missing folders above it too.

**CSV** means comma-separated values: a text table whose first row, the **header**, names the columns. A **channel** identifies a measurement source, such as `bus_voltage`; its **unit** describes the scale, such as `V` for volts or `A` for amperes. CSV quotes protect commas inside a field; use `csv`, rather than splitting lines on commas.

A **dictionary** maps keys to values, such as `{"channel": "bus_voltage"}`. `list[dict[str, Any]]` means a list of dictionaries with string keys; `Any` permits different value types. A **float** is a number that can have a fractional part, such as `24.5`.

**JSON** is a text format for lists, dictionaries, strings, numbers, booleans and `null` (Python's `None`). **Serialization** converts Python data to that text. `indent=2` uses two spaces per indentation level; `sort_keys=True` orders dictionary keys alphabetically, including nested dictionaries.

**UTF-8** is the text encoding (the rule for storing characters as bytes) used throughout this set. A `with` block closes an opened file even if reading fails. For CSV, open with `newline=""` so the CSV module handles Windows and Linux line endings:

```python
from pathlib import Path

notes = Path("operator-note.txt")
with notes.open("w", encoding="utf-8") as output:
    output.write("Station ready\n")
```

## Exercises

For every function, paths may be strings or `Path` objects. CSV inputs have exactly the header `timestamp,channel,value,unit`, followed by valid records and possibly completely empty lines. A header-only file has no records. Preserve channel and unit text exactly. You need not validate headers, field counts or timestamps.

A **timestamp** records when a reading happened. Here each timestamp uses the same fixed-width ISO 8601 form, `YYYY-MM-DDTHH:MM:SSZ`, for example `2026-01-02T09:00:03Z`. `T` separates date and time; `Z` means UTC, the shared world time standard. All readings use UTC and whole seconds, so comparing these strings orders them by time. Error cases described below should escape to the caller; do not replace them with empty results.

### E1 — Read a station log (easy, ~10 min)

**Goal:** Load a measurement CSV. Return one dictionary per record in its original file order, with exactly the four header keys. Convert only `value` to a float; keep the other three fields as strings. Skip completely empty lines.

**Signature:** `def read_measurements(path: str | Path) -> list[dict[str, Any]]`

**Example:** A file containing:

```csv
timestamp,channel,value,unit
2026-01-02T09:00:01Z,bus_voltage,24.50,V
```

returns `[{"timestamp": "2026-01-02T09:00:01Z", "channel": "bus_voltage", "value": 24.5, "unit": "V"}]`.

**Watch out:** A header-only file returns `[]`. Quoted fields can contain commas or non-English characters. A nonnumeric value raises `ValueError`; a missing file raises `FileNotFoundError`.

**Reread:** Python Tutorial §7.2 and §7.2.1 (file objects); `csv` docs, `DictReader` and opening files with `newline=''`.

### E2 — Save the operator's results (easy, ~10 min)

**Goal:** Create all missing parent folders, then write the entire `results` list as UTF-8 JSON with `indent=2` and `sort_keys=True`. Replace existing contents, return `None` and leave the supplied list and dictionaries unchanged.

**Signature:** `def write_results(path: str | Path, results: list[dict[str, Any]]) -> None`

**Example:** `write_results("reports/run-01/results.json", [{"value": 24.5, "channel": "bus_voltage"}])` creates the folders and writes:

```json
[
  {
    "channel": "bus_voltage",
    "value": 24.5
  }
]
```

**Watch out:** Inputs contain only JSON-compatible data. An empty list writes `[]`. A final newline is optional; non-English characters may be written directly or escaped using JSON's character escapes. Existing folders are fine.

**Reread:** `json` docs, `dump`, `indent` and `sort_keys`; `pathlib` docs, `Path.mkdir` with `parents` and `exist_ok`.

### E3 — Find each channel's newest reading (medium, ~10 min)

**Goal:** Read a measurement CSV and return a dictionary mapping each channel to its newest numeric value. Rows can be out of order: choose the largest timestamp for that channel, rather than simply the last row.

**Signature:** `def latest_per_channel(path: str | Path) -> dict[str, float]`

**Example:** If `bus_voltage` appears at `09:00:03Z` with `24.5`, then at `09:00:01Z` with `24.0` on the same date, return `{"bus_voltage": 24.5}`.

**Watch out:** Equal timestamps for the same channel use the value from the later row in the file. A header-only file returns `{}`. Use E1 if helpful; its blank-line, numeric-conversion and missing-file behavior also applies here. The returned dictionary's order does not matter.

**Reread:** `csv` docs, `DictReader`; Python Tutorial §7.2.1, iterating over file contents.

### E4 — Combine logs for a run review (medium, ~15 min)

**Goal:** Combine the records from `paths`, sort them by ascending timestamp and write one CSV to `out_path` with the same four-column header. Return the number of records written, excluding the header. Skip empty lines and keep duplicate records.

**Signature:** `def merge_logs(paths: list[str | Path], out_path: str | Path) -> int`

**Example:** If the first file contains readings at seconds `03`, `01` and the second contains one at `02` on the same date and minute, output seconds `01`, `02`, `03` and return `3`.

**Watch out:** A **stable sort** preserves the original order of records whose sort keys (here, timestamps) are equal. For ties, preserve file order in `paths`, then row order within each file. Preserve every field's text, including numeric spelling such as `024.500`; E1 converts numbers, so it loses that spelling. CSV quoting and line endings may change. Replace an existing output file. With no inputs or only header-only inputs, write just the header and return `0`. The output's parent folder already exists, and output is distinct from every input. A missing input raises `FileNotFoundError`.

**Reread:** `csv` docs, `DictReader`, `DictWriter`, `writeheader` and `writerows`; *Automate the Boring Stuff*, Working with CSV Files and JSON Data. Before recording your finished work, revisit Pro Git §2.2, checking changes with `git diff` and recording them with `git add` and `git commit`.
