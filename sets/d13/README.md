# d13 — Logging and structured reports

**Time:** about 70 minutes · **Read first:** [Python Logging HOWTO, Basic Logging Tutorial](https://docs.python.org/3/howto/logging.html#basic-logging-tutorial); Pro Git [3.5 Remote Branches](https://git-scm.com/book/en/v2/Git-Branching-Remote-Branches); Python [`collections`: Counter and defaultdict](https://docs.python.org/3/library/collections.html) · **You edit:** `starter/reporting.py` and `starter/station_checks.py`

## What you're building

A test station runs checks on instrument channels (named measurement inputs, such as `CH1`). Operators need a readable event log and a machine-readable report to find failed checks and decide whether a run passed. You will build the log helpers, then run fake station checks with pytest and read its report. No instrument or network connection is needed.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/reporting.py` and `starter/station_checks.py`; E4 also needs a test decorator. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: d13** (or run `bash tools/run.sh d13` / `tools\run.ps1 d13` from the repo root). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

**UTF-8** is a text encoding that supports non-English characters. In type hints, `Any` means a value of any Python type; `Path` is a filesystem path object from `pathlib`.

A **logger** receives named events; a **handler** sends them somewhere, such as a file; a **formatter** controls their text. A **level** describes importance: DEBUG < INFO < WARNING < ERROR < CRITICAL. A logger's **propagation** setting controls whether parent loggers also receive its events.

A **status** is a check's outcome: `PASS` means within requirements, `FAIL` means outside requirements, and `ERROR` means the check could not finish. A **Counter** counts repeated values. A **defaultdict** supplies a new default value for a missing key, such as an empty list for a channel. Convert either to an ordinary `dict` when returning results.

```python
from collections import Counter, defaultdict
visits = Counter(["CH2", "CH2", "CH4"])
notes = defaultdict(list)
notes["CH4"].append("connector reseated")
print(visits["CH2"], notes["CH4"])  # 2 ['connector reseated']
```

**Metadata** describes the hardware used for a test, such as its station ID (identifier) and serial number (the hardware unit's identifying label).

For E2–E3, every input result is a dictionary containing string keys `channel`, `status`, and `message`; all three values are strings. Status is always exactly `PASS`, `FAIL`, or `ERROR`. Other fields may be present. Inputs are valid; you do not need to validate malformed results. Do not change input dictionaries or lists. File paths accept `str` or `pathlib.Path`; parent directories already exist. Let file errors reach the caller.

## Exercises

### E1 — Station event log (easy, ~12 min)

**Goal:** Return the named `logging.Logger`, configured to append UTF-8 text to the supplied file. Set both logger and file handler to INFO, and set `propagate = False`. Use this exact formatter string: `"%(asctime)s %(levelname)s %(name)s: %(message)s"`, with logging's default timestamp format. Each accepted event occupies one line for the single-line messages used here.

**Signature:** `def get_station_logger(name: str, path: str | Path) -> logging.Logger`

**Example:** After `log = get_station_logger("station.chassis", "run.log")`, `log.info("power enabled")` adds a line ending `INFO station.chassis: power enabled`.

**Watch out:** DEBUG events must be omitted; INFO through CRITICAL must be recorded. Repeating a call with the same name and same path returns the same logger with exactly one file handler, so each event appears once. Existing file text stays intact. Different names use independent files. Names are fresh on first call; reconfiguring a name for a different path or handling externally installed handlers is outside this exercise. The caller owns closing the returned logger's handlers when finished; do not close them inside the function. No root logger configuration is needed.

**Reread:** Logging HOWTO → “Logging to a file”, “Logging from multiple modules”, “Changing the format of displayed messages”, and “Displaying the date/time in messages”. The supplied `logging` module exposes `FileHandler` and `Formatter` for the named-logger setup.

### E2 — Overall run outcome (easy, ~10 min)

**Goal:** Use `Counter` to count result statuses. Return exactly `{"counts": <ordinary dict of observed statuses and counts>, "overall": <worst status>}`. Worst means `ERROR` before `FAIL` before `PASS`, regardless of input order. Include only observed statuses in `counts`. Empty input returns `{"counts": {}, "overall": "ERROR"}`: no results cannot establish a passing run.

**Signature:** `def summarize(results: list[dict[str, Any]]) -> dict[str, Any]`

**Example:** Two PASS results and one FAIL result → `{"counts": {"PASS": 2, "FAIL": 1}, "overall": "FAIL"}`. Dictionary key order does not matter.

**Watch out:** Count checks, not distinct channels: repeated checks on one channel count separately. Status severity is a stated rule, not alphabetical order or the most frequent status.

**Reread:** `collections` → “Counter objects”; Logging HOWTO → “When to use logging” for the related idea of event importance. Result statuses here are separate from logging levels.

### E3 — Operator failure list (easy, ~9 min)

**Goal:** Use `defaultdict(list)` to collect messages from FAIL and ERROR results under their channel names. Return an ordinary dictionary mapping each affected channel to its list of messages. Omit PASS results and channels without failures. Within each channel, keep input order and repeated or empty messages. Empty input returns `{}`.

**Signature:** `def failures_by_channel(results: list[dict[str, Any]]) -> dict[str, list[str]]`

**Example:** FAIL `CH1: voltage low`, PASS `CH2: ready`, ERROR `CH1: timeout` → `{"CH1": ["voltage low", "timeout"]}`.

**Watch out:** Each channel needs its own list. A message reports what happened; it need not be unique. Dictionary key order does not matter.

**Reread:** `collections` → “defaultdict objects” and its examples of grouping values into lists; Logging HOWTO → “Logging variable data”.

### E4 — Run pytest and read its JUnit report (medium, ~39 min)

**Goal:** Write a small pytest test module (a Python file containing tests) for a fake station check, run it to create a report, then read every test's outcome and hardware metadata. Budget about 10 minutes for the guidance below and 29 minutes for the lab.

**Reporting guidance (read before coding):** **CI** (continuous integration) runs automated checks when code changes. **JUnit XML** is a report format that CI systems read to display individual test results. **XML** stores data in named elements, such as `<testcase>`, with attributes (named values in an opening tag) and child elements nested inside. JUnit is a format name here; pytest writes it directly, and you do not need Java.

A pytest **fixture** prepares a test before its body runs. A failed `assert` in the test body becomes a `<failure>` child; an exception during fixture setup becomes an `<error>` child because the check could not run. A passing test has neither. A skipped test (a check deliberately not run) has `<skipped>`. These become `FAIL`, `ERROR`, `PASS`, and `SKIP` in your reader; these labels are separate from E2's application statuses.

**Parametrization** runs one test function with several input rows. Its `ids` argument gives each row a readable name in square brackets, such as `test_e4_voltage[nominal]`. A **decorator** is a line starting with `@` above a function that configures it. `indirect=["fixture_name"]` sends that parameter through the named fixture, where `request.param` holds the row's input; ordinary parameters go straight to the test function.

```python
@pytest.mark.parametrize(
    "relay_ready, channel", [("connected", 2)],
    ids=["relay-channel-two"], indirect=["relay_ready"],
)
def test_relay(relay_ready, channel):
    assert channel > 0
```

Here `relay_ready` would be a fixture you define; pytest supplies `channel` directly. This example only shows the decorator pattern.

pytest supplies `record_property`, a fixture whose value is a function you call as `record_property("name", value)`. Each call adds a property under the current test's `<properties>` element, including when another fixture later fails. Record hardware metadata before the operation that might raise. Use `-o junit_family=xunit1` for this lab: `xunit1` is pytest's older XML layout that supports per-test properties. The default `xunit2` layout warns that custom properties do not fit its schema (the format's rules).

Python's standard-library `xml.etree.ElementTree` (imported as `ET` in your starter) reads XML. `ET.parse(path).getroot()` loads a file's outer element, `.iter("testcase")` visits test cases in document order, `.find("failure")` finds a direct child or returns `None`, and `.findall("properties/property")` finds properties inside that test. An element's `.attrib` is its attribute dictionary. Check `element is not None`, rather than relying on an element's truth value: an empty child still records a failure.

**Part A — Author the station module.** Edit `starter/station_checks.py`. Keep the supplied names and signatures; do not add other tests or change the two metadata constants.

1. Complete the `station_ready` fixture. Call `record_property` for `station_id` with `STATION_ID` and `serial_number` with `SERIAL_NUMBER`, once each. Then, if `request.param == "offline"`, raise `RuntimeError("station offline")`. In `"ready"` mode, finish normally without returning a value. The supplied `Callable` type hint means a function you can call; this one takes a property name and value and returns `None`.
2. Add `@pytest.mark.parametrize` above `test_e4_voltage`, using parameter names `"station_ready, voltage"`, the rows below in this order, their exact `ids`, and `indirect=["station_ready"]`.

| Fixture mode | Voltage (V, volts) | ID | Expected result |
| --- | --- | --- | --- |
| `"ready"` | `5.0` | `"nominal"` | PASS |
| `"ready"` | `4.0` | `"undervoltage"` | FAIL |
| `"offline"` | `5.0` | `"offline"` | ERROR |

3. Complete `test_e4_voltage` with an assertion that the actual `voltage` is between `4.8` and `5.2`, including both limits. Do not force a failure based on a row's ID or catch the intentional failures. The `station_ready` argument makes pytest run the fixture first; its value is `None`.
4. From the repo root, with the course Python environment active, run:

```text
python -m pytest sets/d13/starter/station_checks.py -q --junitxml=sets/d13/station.xml -o junit_family=xunit1
```

`--junitxml` selects the output file. This command intentionally exits with code `1` and reports `1 failed, 1 passed, 1 error`. Open `sets/d13/station.xml` and find the three case names, the `<failure>` and `<error>`, and both hardware properties on every case. The d13 grader runs this module in a separate Python process (a subprocess) in a temporary directory, so these intentional outcomes do not make E4 fail when implemented correctly.

**Part B — Read the report.** Replace the E4 stub in `starter/reporting.py`.

**Signature:** `def read_junit(path: str | Path) -> list[dict[str, Any]]`

Return one dictionary per `<testcase>`, in XML document order, with exactly these keys:

- `name`: its `name` attribute, including any bracketed parameter ID.
- `outcome`: `"ERROR"` if it has an `<error>` child, otherwise `"FAIL"` for `<failure>`, otherwise `"SKIP"` for `<skipped>`, otherwise `"PASS"`.
- `properties`: an ordinary dictionary of each `<properties>/<property>` child's `name` and `value` attributes. Values stay strings. Use `{}` when properties are absent.

Accept either `<testsuite>` (one group of tests) or `<testsuites>` (several groups) as the outer element. Visit all test cases, even across multiple groups. Every test case has a name; property names are unique within a test and have value attributes. Other XML attributes and elements may be ignored. Empty reports return `[]`. Let file errors and `ET.ParseError` (ElementTree's exception for malformed XML) reach the caller. Do not modify the report or read pytest's console text instead of XML.

**Example:** Reading the report from Part A returns:

```python
[
    {"name": "test_e4_voltage[nominal]", "outcome": "PASS", "properties": {"station_id": "CHASSIS-A1", "serial_number": "SN-0042"}},
    {"name": "test_e4_voltage[undervoltage]", "outcome": "FAIL", "properties": {"station_id": "CHASSIS-A1", "serial_number": "SN-0042"}},
    {"name": "test_e4_voltage[offline]", "outcome": "ERROR", "properties": {"station_id": "CHASSIS-A1", "serial_number": "SN-0042"}},
]
```

**Watch out:** A fixture error is not an assertion failure. Read properties from each test case, including the offline case. The station module's intentional failures are evidence to inspect; the normal **Test: d13** command grades both your authored tests and your reader and should show `Exercises: 4 / 4 passed` when all exercises are complete.

**Reread:** The reporting guidance above; pytest → “Creating JUnitXML format files”, “record_property”, and “Indirect parametrization”; Python `xml.etree.ElementTree` → “Finding interesting elements”. Pro Git 3.5 → “Tracking Branches” remains today's workflow reading; the rebasing reading's 25 minutes now belong to this lab.
