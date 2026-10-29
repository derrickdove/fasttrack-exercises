# d06 — Modeling results: classes, dataclasses and enums

**Time:** about 45 minutes · **Read first:** [Python Tutorial §9.1–9.8: Classes](https://docs.python.org/3/tutorial/classes.html), [Pro Git 3.1–3.2: Branches in a Nutshell and Basic Branching and Merging](https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell), [dataclasses: Data Classes](https://docs.python.org/3/library/dataclasses.html), and [enum: Enum](https://docs.python.org/3/library/enum.html#enum.Enum) · **You edit:** `starter/models.py`

## What you're building

A test station is a setup that measures hardware and checks whether it works. Its instruments produce readings on named channels (measurement inputs such as `supply` or `load`). You'll model check outcomes, preserve individual readings, and maintain statistics that an operator can use to review a run.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/models.py`. Don't edit `tests/`. The imports, enum members, dataclass fields, and method signatures are supplied.
2. Press **Ctrl+Shift+B → Test: d06** (or run `bash tools/run.sh d06` / `tools\run.ps1 d06` from the repo root). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

Work in order: E4 uses the classes from E2 and E3. The Git reading explains a **branch**, a separate line of development, and **merging**, combining branch changes; use that workflow if you want to keep your practice separate. No Git command is graded here.

A **class** defines a kind of object; an **instance** is one object made from it. A **method** is a function belonging to a class; `self` refers to the instance. `__init__` initializes a new instance. An **attribute** stores or exposes a value on an object; a **property** exposes a method's result using attribute syntax, such as `device.label`:

```python
class Instrument:
    def __init__(self, label: str) -> None:
        self.label = label
meter = Instrument("bench meter")
print(meter.label)  # bench meter
```

An **enum** defines named choices, such as `Status.PASS`; supplied `auto()` calls give each member a distinct value. Those values do not express severity. An **iterable** supplies items one at a time, such as a list or a generator; a generator may be consumed only once.

A **dataclass** generates methods such as initialization and field-by-field equality from declared fields. A **decorator** is an `@...` line that changes how a class or function is created. `@dataclass(frozen=True)` makes fields **immutable**, meaning they cannot be reassigned after creation. The generated initializer calls `__post_init__` for your extra validation. A **type hint**, such as `-> float`, describes an expected type; it does not validate values for you. `ValueError` signals an unacceptable value; `raise` reports that exception to the caller. Tests using `pytest.raises` require that exception.

## Exercises

### E1 — Choose a run's worst outcome (easy, ~7 min)

**Goal:** Combine individual hardware checks into one outcome. `PASS` means a check met its limits, `FAIL` means it did not, and `ERROR` means the check could not produce a trustworthy result.

**Signature:** `class Status(Enum)` with distinct `PASS`, `FAIL`, `ERROR` members (supplied); `def worst(statuses: Iterable[Status]) -> Status`.

Return the most severe member: `ERROR` wins over `FAIL`, which wins over `PASS`. Return `ERROR` for an empty iterable because no checks ran. Inputs contain only `Status` members. Accept lists, tuples, and generators without needing a second pass over them. Member numeric values are not part of the contract.

**Example:** `worst([Status.PASS, Status.FAIL])` → `Status.FAIL`; `worst([])` → `Status.ERROR`.

**Watch out:** Enum members do not support severity comparisons with `>` automatically. Return a `Status`, not its name as text.

**Reread:** Python Tutorial §9.3.1, Class Definition Syntax, and §9.3.2, Class Objects; enum documentation, `Enum` and `auto`.

### E2 — Preserve and convert an instrument reading (medium, ~15 min)

**Goal:** Make an immutable record of one measurement and return converted copies when the operator changes display units.

**Signatures:** `@dataclass(frozen=True) class Reading(channel: str, value: float, unit: str)`, `def __post_init__(self) -> None`, and `def to_unit(self, unit: str) -> "Reading"`.

- Construction raises `ValueError` if `channel == ""` or the value is not **finite** (a regular number rather than infinity or NaN, the special “not a number” value). `math.isfinite`, imported for you, checks this. Negative and zero values are valid. Preserve non-empty channel text exactly; do not strip spaces. Input types match the hints; you need not check types.
- Construction accepts any unit string; validate supported units when converting. A **unit** gives a number physical meaning: `V` is volts (voltage), `A` is amperes (electric current); `mV` and `mA` are their milli-units, one thousandth as large.
- `to_unit` returns a **new** `Reading` with the same channel and the requested unit. Convert `V` → `mV` and `A` → `mA` by multiplying by 1000; reverse conversions divide by 1000. Requesting the same supported unit returns a new, equal reading.
- Raise `ValueError` for unknown source or target units, including an unknown unit converted to itself, and for crossing voltage/current families. Unit labels are case-sensitive. The converted reading must also have a finite value; raise `ValueError` if conversion makes it infinite. Keep the original unchanged.

**Example:** `Reading("supply", 1.25, "V").to_unit("mV")` → `Reading(channel="supply", value=1250.0, unit="mV")`.

**Watch out:** Keep the supplied frozen decorator. You only write validation and conversion; the dataclass supplies initialization and equality. Tests compare computed decimal values with a small tolerance for floating-point rounding.

**Reread:** Python Tutorial §9.3.2–9.3.4, Class Objects through Method Objects; dataclasses documentation, `__post_init__` under Post-init processing, and Frozen instances.

### E3 — Keep running statistics for one signal (medium, ~12 min)

**Goal:** Update a signal's statistics as each measurement arrives, without storing its entire history.

**Signatures:** `RunningStats()`, `def add(self, value: float) -> None`, and read-only properties `count: int`, `mean: float`, `min: float`, `max: float`.

A **running statistic** updates a stored result when a new sample arrives; a **sample** is one measured number. New instances start with `count == 0`. Every `add` includes one finite number and returns `None`. Inputs here are finite numbers; additional validation is not required. `count` is the number added, `mean` is their sum divided by count (the arithmetic average), and `min`/`max` are the smallest/largest values seen. Accessing **any** of `mean`, `min`, or `max` on an empty instance raises `ValueError`.

All four properties are read-only: callers may read them but may not assign to them. Instances must keep independent state. Use **O(1)** work and storage: a fixed amount per `add` and property read, independent of how many samples came before. Keep a count, total, and extrema (smallest and largest values), rather than a growing list. Values in the tests keep totals within the finite range.

**Example:** after `stats = RunningStats(); stats.add(12.0); stats.add(10.0)`, `(stats.count, stats.mean, stats.min, stats.max)` → `(2, 11.0, 10.0, 12.0)`.

**Watch out:** Don't initialize extrema to zero; the first sample might be positive or negative. The speed check allows 2 seconds for 200,000 updates with property reads. The property called `min` belongs to your instance; Python's separate `min(...)` function still exists.

**Reread:** Python Tutorial §9.3.3–9.3.5, Instance Objects, Method Objects, and Class and Instance Variables; §9.4, Random Remarks, for methods calling other methods. Use the supplied `@property` decorators to expose getters without parentheses.

### E4 — Group channels for an operator summary (medium, ~11 min)

**Goal:** Build a **channel bank**, a collection holding one `RunningStats` for each distinct channel name, so the operator can review every signal.

**Signatures:** `ChannelBank()`, `def add(self, reading: Reading) -> None`, `def summary(self) -> dict[str, dict[str, int | float | str]]`, and `def __len__(self) -> int`.

- A new bank has no channels: `len(bank) == 0` and `bank.summary() == {}`. Python calls `__len__` for `len(bank)`.
- `add` receives an already-valid `Reading`, creates a `RunningStats` when that channel first appears, adds its value, and returns `None`. Different channel names have independent statistics, even if their readings arrive interleaved. Count distinct names, not samples. Banks must also be independent of each other.
- Remember each channel's first unit string. Subsequent readings for that channel must have **exactly** the same unit string; otherwise raise `ValueError` before changing any state. The bank accepts any unit label when consistent within a channel. It does not convert units: if needed, call `to_unit` before `add`.
- `summary` returns one dictionary per channel, with **exactly** the keys `unit`, `count`, `mean`, `min`, `max`. `unit` is the remembered string; the other values come from that channel's `RunningStats`. Dictionary order does not matter.
- Every call returns fresh outer and inner dictionaries: changing the returned summary cannot change the bank, and later adds cannot change an older summary. This is a **snapshot**, a detached view of the values at one moment. Do not expose the bank's internal dictionaries.

**Example:** after `bank.add(Reading("supply", 12.0, "V"))` and `bank.add(Reading("supply", 10.0, "V"))`, `bank.summary()` → `{"supply": {"unit": "V", "count": 2, "mean": 11.0, "min": 10.0, "max": 12.0}}`, and `len(bank)` → `1`.

**Watch out:** Adding `Reading("supply", 1000.0, "mV")` to that bank must fail without incrementing the count. Creating a fresh outer dictionary alone does not protect shared inner dictionaries.

**Reread:** Python Tutorial §9.3.5, Class and Instance Variables, for independent state; §9.4, Random Remarks, for one object's methods using another object. Review Pro Git §3.2, Basic Branching and Merging, when combining your practice branch changes.
