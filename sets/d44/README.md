# d44 — Verification language: requirements and traceability

**Time:** about 45 minutes · **Read first:** [NASA Systems Engineering Handbook §5.3, Product Verification](https://www.nasa.gov/reference/5-3-product-verification/); glossary pass below (one-line meanings in the NASA handbook/job-posting context); [Wikipedia, Hardware-in-the-loop simulation](https://en.wikipedia.org/wiki/Hardware-in-the-loop_simulation), overview · **You edit:** `starter/trace.py`

## What you're building

A chassis test station needs evidence that its requirements were checked. A **requirement** is a stated condition the product must satisfy; **verification** gathers evidence that it does; **traceability** links each requirement to that evidence. Build a small coverage report and a **traceability matrix**, a table showing those links, so an operator can spot missing checks before a review.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/trace.py`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d44** (or run `bash tools/run.sh d44` / `tools\run.ps1 d44`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

A glossary pass for the station vocabulary:

- **EMI (electromagnetic interference):** unwanted electromagnetic energy that can disturb electronics or signals.
- **TVAC (thermal vacuum):** checking equipment in low pressure while controlling temperature to represent a space environment.
- **Harness checks:** inspections or electrical checks of a cable assembly's connections, wiring, and labels.
- **ATE (automated test equipment):** instruments and software that run checks and record results with limited operator work.
- **UUT (unit under test):** the particular product connected to the station for checking.
- **HIL (hardware-in-the-loop):** testing real hardware connected to a simulation that responds as its surrounding system would.

The four **verification methods**, or ways to gather evidence, are **Test** (measure behavior under controlled conditions), **Analysis** (use calculations or models), **Inspection** (examine physical features or records), and **Demonstration** (show an observable capability in operation).

A **dictionary** maps a key (a lookup label) to a value; here the outer key is a requirement identifier (**id**, a unique label). A **list** holds multiple records. **CSV** is a text table with comma-separated fields; use `csv` so quoted commas work. **JSON** stores structured data as text; `json.load` turns the supplied log into Python lists and dictionaries. A **set** stores unique values; `sorted` returns a new list in ascending order. A `pathlib.Path` represents a file or directory location. **UTF-8** is the text encoding used for these files.

```python
import csv
import io

rows = csv.DictReader(io.StringIO('channel,note\nCH1,"supply, startup"\n'))
notes = {row["channel"]: row["note"] for row in rows}
print(notes["CH1"])  # supply, startup
```

### Shared data contract

`Requirements` means `dict[str, dict[str, str]]`. For example:

```python
reqs = {"REQ-01": {"id": "REQ-01", "text": "Supply shall meet limits.", "method": "Test"}}
results = [{"req_id": "REQ-01", "test_name": "startup_voltage", "status": "PASS"}]
```

`Results` means `list[dict[str, str]]`. Each record has exactly `req_id`, `test_name`, and `status`; names and ids are nonempty strings and status is exactly `PASS` or `FAIL`. The caller loads `data/results.json` with `json.load`; none of your functions needs to load that file. `test_name` labels any evidence-producing check, including an inspection or demonstration. Multiple records can refer to the same requirement or check.

**Coverage** means accounting for the evidence available for each requirement. For E2–E4, inputs already follow these shapes, requirements have valid methods, and each dictionary key equals its inner `id`. Do not strip or otherwise change them. Ignore evidence whose `req_id` is absent from `reqs`, and never mutate either input. No additional input validation is required in E2–E4.

A requirement is `failed` if **any** matching record is `FAIL`, otherwise `verified` if it has at least one `PASS`, otherwise `not-run`. This is a simplified evidence rule for this exercise, applied to all four methods. A later pass does not erase a failure; real acceptance also needs the planned procedure and review. Every output list and matrix row uses ascending, case-sensitive string order of requirement ids, regardless of input order.

## Exercises

### E1 — Read the verification plan (easy, ~14 min)

**Goal:** Load the station's requirement records from a UTF-8 CSV file.

**Signature:** `def load_requirements(path: str | Path) -> Requirements`

**Contract:** The header must contain exactly `id,text,method`, once each, in any order. Strip surrounding whitespace from every data field (not the header); keep interior whitespace and capitalization. Each nonblank row must have exactly three fields, all nonempty after stripping. `method` must be exactly `Test`, `Analysis`, `Inspection`, or `Demonstration`. Reject duplicate ids after stripping. Raise `ValueError` for an invalid header or row; the error message is your choice. Completely empty lines are ignored. A valid header with no data returns `{}`; an empty file is invalid. Let file errors such as `FileNotFoundError` propagate.

**Example:** A row `REQ-01,Supply shall meet limits.,Test` becomes `{"REQ-01": {"id": "REQ-01", "text": "Supply shall meet limits.", "method": "Test"}}`.

**Watch out:** A quoted comma belongs inside its field. Use `csv.reader` or `csv.DictReader`, open with `encoding="utf-8", newline=""`, and accept either a string path or `pathlib.Path`. `data/requirements.csv` supplies all four methods.

**Reread:** NASA §5.3, Product Verification: the discussion of verification methods and preparing verification activities.

### E2 — Summarize evidence coverage (easy/medium, ~11 min)

**Goal:** Tell the operator which requirements have passing evidence, failures, or no recorded check.

**Signature:** `def coverage(reqs: Requirements, results: Results) -> dict[str, list[str]]`

**Contract:** Return exactly the keys `verified`, `failed`, and `not-run`, each mapping to a sorted list of requirement ids. Follow the shared evidence rule. Include every known requirement in exactly one list; with no requirements return three empty lists.

**Example:** For the shared one-requirement example, return `{"verified": ["REQ-01"], "failed": [], "not-run": []}`. For the supplied files: verified is `REQ-01, REQ-04, REQ-06`; failed is `REQ-02`; not-run is `REQ-03, REQ-05` (each shown here as a list of ids).

**Watch out:** Record order must not change the outcome. Ignore `RETIRED-99` in the supplied log because the plan no longer contains it. Duplicate passes still produce one id.

**Reread:** NASA §5.3, Product Verification: comparing verification results with requirements and recording the evidence.

### E3 — Find tests that have not run (easy, ~7 min)

**Goal:** Produce the station's remaining Test-method work list.

**Signature:** `def untested(reqs: Requirements, results: Results) -> list[str]`

**Contract:** Return only ids whose method is exactly `Test` and whose coverage status is `not-run`, sorted. A failed test has run, so it is not untested. Missing Analysis, Inspection, and Demonstration evidence never belongs in this list. Empty inputs return `[]`.

**Example:** With the supplied files, `untested(reqs, results)` returns `["REQ-03"]`.

**Watch out:** Missing evidence is different from failed evidence. You may reuse E2.

**Reread:** NASA §5.3, the four verification methods; the glossary's EMI and TVAC entries; Wikipedia's HIL overview for an example of where Test evidence can come from.

### E4 — Export the review matrix (medium, ~13 min)

**Goal:** Write a CSV table the operator can open during the station verification review.

**Signature:** `def matrix_csv(reqs: Requirements, results: Results, path: str | Path) -> None`

**Contract:** Create or overwrite the UTF-8 file at `path` with exactly this header: `req_id,method,test_names,status`. Write one row per known requirement, sorted by id. Copy its method; join its unique matching `test_name` values in sorted order with `;` and no added spaces. Use an empty field when there are no names. Status is exactly `verified`, `failed`, or `not-run`, using E2's rule. Empty requirements still write the header. Return `None`. The parent directory already exists; propagate file errors. Use `csv.writer` or `csv.DictWriter` and `newline=""`; either standard CSV line ending is accepted. Accept a string or `Path`.

**Example:** One output row for the supplied files is `REQ-02,Test,command_latency;command_retry,failed`.

**Watch out:** Preserve names verbatim; quote commas, quotes, or newlines through the CSV library. Names in this exercise never contain `;`. Include non-Test requirements too. You may reuse E2.

**Reread:** NASA §5.3, Product Verification: documenting results and maintaining links between requirements and verification evidence.
