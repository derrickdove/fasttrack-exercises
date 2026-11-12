# p05 — Classes from zero

**Time:** about 65 minutes · **Read first:** [Python Tutorial 9.3, a first look at classes](https://docs.python.org/3/tutorial/classes.html#a-first-look-at-classes) and [the dataclasses introduction](https://docs.python.org/3/library/dataclasses.html) · **You edit:** `starter/objects.py`

## What you're building

A **test station** is a computer and equipment used to check hardware. An **instrument** measures or controls something; a power supply is an instrument that provides electrical power. An **operator** is the person running the station. You will keep named measurements, remember station events, and switch a pretend supply without connecting hardware.

This set prepares you for [d06](../d06/README.md), which adds richer reading records and statistics. E8 prepares you for [d19](../d19/README.md), which builds drivers handed a connection. Here you only send two commands; you do not need networks, instrument software, or equipment.

## How this works

1. Open `starter/objects.py`. Replace the `raise NotImplementedError(...)` lines for one exercise at a time. `NotImplementedError` marks unfinished code. Keep all class and function names. E9 has special instructions for replacing a whole method. Leave the already complete `FakeLink` alone. Don't edit `tests/`.
2. Save, then run `bash tools/run.sh p05` from the repository folder in the **shell**, the terminal program that runs commands. At first expect `Exercises: 0 / 11 passed`. Run again after each exercise; all tests for an exercise must pass before its score changes.
3. Work through the 11 exercises in order. E2 uses E1, E6 uses E3, and E10 combines E2 and E3 with the loop pattern below. Report **all pass / partial / stuck** in the tracker. Stop around 65 minutes and report where you reached.

Python examples below go in a temporary Python file or the Python interactive prompt, not directly at the shell prompt. Do not type prompt marks such as `>>>`. Each worked example runs by itself. Exercise examples assume you have finished the named class in `objects.py`.

A **function** is named code you call; a **parameter** is an input name in its definition. A **signature** is the `def` line showing those inputs and the result type. A **type hint** describes a type: `str` is text, `float` is a number that can have a fractional part, `int` is a whole number, and `bool` is `True` or `False`. `None` means no result value. Hints guide you; they do not check input values while your code runs.

Syntax to keep beside you:

- `def` defines a function. A `:` after a header starts its indented block; **indentation**, the spaces at the start of a line, shows which block owns that line. Use four spaces per level.
- In `name: str`, `:` introduces a type hint; `->` introduces the result type. `()` calls code; values inside are inputs, separated by commas. In a definition, the parentheses hold parameter names instead.
- `=` stores a value; `==` asks whether two values are equal. Quotes such as `"ready"` make text. A dot, as in `station.label`, accesses something belonging to an object.
- A **loop** repeats code; `for item in items:` visits each item in order and runs the indented block once for that item.
- `return` sends a result back to the caller. `print(...)` only displays it. A function without a `return` value gives back `None`. `#` starts a comment, text Python ignores.

All inputs have the stated types. Numbers are ordinary finite numbers, and `low <= high` wherever both limits occur. `<=` means less than or equal to. Only E5 asks you to reject input. Do not round numbers, print exercise results, or connect to hardware.

## Exercises

### E1 — Keep a named reading (easy, ~6 min)

**Goal:** Keep a measurement's name and value together so the station knows what it measured. A **reading** is one measured number with its name.

**New idea:** An **object** groups data and actions; a **class** describes its kind, and an **instance** is one object made from that class. An **attribute** is a value stored on an object, and a **method** is a function defined inside a class. **`__init__`** is the method Python calls to set up a new instance; **`self`** means that particular instance. In `Instrument("meter", "bench")`, Python supplies `self` automatically, so the caller only supplies the other two inputs.

```python
class Instrument:
    def __init__(self, label: str, location: str) -> None:
        self.label = label
        self.location = location
meter = Instrument("meter", "bench")
print(meter.location)  # bench
```

**Signature:** In `class Reading`: `def __init__(self, name: str, value: float) -> None:`

**Examples:**

```python
reading = Reading("supply", 5.0)
reading.name   # "supply"
reading.value  # 5.0
Reading("load", 0.2).value  # 0.2
```

**Contract:** Store the supplied inputs as `self.name` and `self.value` without changing them. Initialize this object; do not return or print a reading from `__init__`.

**If you're stuck:** Hint 1: A plain local name disappears after setup, but an attribute belongs to the object. Hint 2: Use the shape `self.attribute = parameter` once for each input.

### E2 — Ask a reading whether it passes (easy, ~5 min)

**Goal:** Ask one reading whether its value is inside the station's allowed limits. A **limit** is an allowed boundary; **inclusive** limits allow equality.

**New idea:** A method can read attributes saved by `__init__`. Call it on the instance, and Python supplies that instance as `self` again. A comparison returns a `bool`; a chain such as `1 <= amount <= 4` checks both boundaries. `>=` means greater than or equal to.

```python
class SpareParts:
    def __init__(self, amount: int) -> None:
        self.amount = amount
    def enough(self, needed: int) -> bool:
        return self.amount >= needed
parts = SpareParts(3)
print(parts.enough(2))  # True
```

You pass `needed`, not `self`, in the example call.

**Signature:** In `Reading`: `def within(self, low: float, high: float) -> bool:`

**Examples:**

```python
Reading("supply", 5.0).within(4.5, 5.5)  # True
Reading("supply", 4.5).within(4.5, 5.5)  # True
Reading("supply", 6.0).within(4.5, 5.5)  # False
```

**Contract:** Return `True` when the stored value is between `low` and `high`, including both ends; otherwise return `False`. Leave the reading unchanged.

**If you're stuck:** Hint 1: The measured value is already inside this object. Hint 2: Use `return` with a comparison chain and read `self.value`.

### E3 — Remember events between calls (easy, ~5 min)

**Goal:** Count completed station events. Calling `record()` means one more event happened.

**New idea:** An object's **state** is the information it remembers between calls. A method can change an attribute rather than return a new value. `+` adds numbers; `self.level = self.level + 2` reads the old level, adds two, and stores the new level.

```python
class Dial:
    def __init__(self) -> None:
        self.level = 0
    def advance(self) -> None:
        self.level = self.level + 2
dial = Dial()
dial.advance()
print(dial.level)  # 2
```

**Signature:** In `EventCount`: `def __init__(self) -> None:` and `def record(self) -> None:`

**Examples:**

```python
events = EventCount()
events.count  # 0
events.record()  # None; events.count is now 1
events.record()  # None; events.count is now 2
```

**Contract:** Each new counter starts with `count` equal to `0`. Each `record()` increases its count by exactly one and returns `None`.

**If you're stuck:** Hint 1: Start the count once, when the object is created. Hint 2: Assign `self.count` in `__init__`, then use the read-add-store shape inside `record`.

### E4 — Give each run its own list (easy, ~6 min)

**Goal:** Keep the messages for two station runs separate. A message added to one run must not appear in another.

**New idea:** A **list** is an ordered collection; `[]` creates an empty list, and `list[str]` hints that its items are text. `append(text)` adds one item at the end of an existing list.

A list written directly under `class`, outside `__init__`, causes the **shared-list trap**, an accidental use of one list by many objects: appending through one object can affect what another sees. Create the list inside `__init__` so each new object gets its own list.

```python
class ToolTray:
    def __init__(self) -> None:
        self.tools: list[str] = []
    def put(self, tool: str) -> None:
        self.tools.append(tool)
tray = ToolTray()
tray.put("probe")
print(tray.tools)  # ["probe"]
```

**Signature:** In `EventLog`: `def __init__(self) -> None:` and `def add(self, text: str) -> None:`

**Examples:**

```python
first = EventLog()
second = EventLog()
first.add("started")  # None; first.messages is ["started"]
second.messages  # []
second.add("ready")  # None; second.messages is ["ready"]
```

**Contract:** A new log has its own empty `messages` list. `add(text)` appends the supplied text in call order and returns `None`. Other logs keep their own messages.

**If you're stuck:** Hint 1: Creating a log must also create a fresh list. Hint 2: Put `self.messages: list[str] = []` inside `__init__`, then use `.append(...)` in `add`.

### E5 — Refuse an impossible channel (easy, ~5 min)

**Goal:** Stop the operator from creating a channel numbered zero or below. A **channel** is a numbered connection on the station.

**New idea:** An **exception** is an error reported to the caller; `ValueError` means an input has an unacceptable value. `raise ValueError("message")` stops the current call and reports that error. An `if` block runs only when its condition is true; `<` means strictly less than.

```python
class RetryBudget:
    def __init__(self, attempts: int) -> None:
        if attempts < 0:
            raise ValueError("Attempts cannot be negative")
        self.attempts = attempts
budget = RetryBudget(0)
print(budget.attempts)  # 0
```

**Signature:** In `Channel`: `def __init__(self, number: int) -> None:`

**Examples:**

```python
Channel(1).number  # 1
Channel(4).number  # 4
Channel(0)  # raises ValueError
```

**Contract:** Raise `ValueError` when `number` is below `1`; any error message is acceptable. Otherwise store it as `self.number`. There is no upper limit here.

**If you're stuck:** Hint 1: Check the number before storing it. Hint 2: Use an `if number < ...:` block containing `raise ValueError(...)`.

### E6 — Reuse a method on the same object (easy, ~4 min)

**Goal:** Record two station events with one call. Reuse your existing `record` behavior.

**New idea:** One method can call another method on `self`. The second method sees the same object's state. Keep the parentheses: `self.message()` runs a method, while `self.message` only refers to it.

```python
class Indicator:
    def message(self) -> str:
        return "READY"
    def show(self) -> str:
        return self.message()
light = Indicator()
print(light.show())  # READY
```

**Signature:** In `EventCount`: `def record_pair(self) -> None:`

**Examples:**

```python
events = EventCount()
events.record_pair()  # None; events.count is 2
events.record_pair()  # None; events.count is 4
events.record()  # None; events.count is 5
```

**Contract:** Call `self.record()` twice, rather than doing the arithmetic again. Keep the existing count and return `None`.

**If you're stuck:** Hint 1: `self` is the counter that needs both events. Hint 2: Write two method-call statements using `self.record(...)`; E3's method takes no extra input.

### E7 — Write your own station error (easy, ~8 min)

**Goal:** Keep a station failure's message and channel number together. Make an error object that other station code can raise.

**New idea:** **Inheritance** means building a class on another class; `class BenchError(Exception):` builds on Python's `Exception` class. `super().__init__(message)` runs that parent class's setup so it keeps the error message. Then `str(error)` gives that message unless you supply **`__str__`**, the method that returns custom text for `str(error)`. `error.args` holds what was passed to `Exception` as a **tuple**, an ordered group of values: `(message,)` has one item, the comma makes it a tuple, and `error.args[0]` reads its first item.

```python
class BenchError(Exception):
    def __init__(self, message: str, bay: int) -> None:
        self.bay = bay
        super().__init__(message)
    def __str__(self) -> str:
        return "Bench error: " + str(self.args[0])
error = BenchError("No response", 2)
print(str(error), error.bay, error.args)  # Bench error: No response 2 ('No response',)
```

**Signature:** In `class StationError(Exception)`: `def __init__(self, message: str, channel: int) -> None:`

**Examples:**

```python
error = StationError("No answer", 3)
error.channel  # 3
str(error)  # "No answer"
error.args  # ("No answer",)
StationError("Wrong mode", 1).channel  # 1
```

**Contract:** Store the channel unchanged as `self.channel` and call `super().__init__(message)`. Keep `Exception`'s own string behavior, so `str(error)` is the message and `error.args` is `(message,)`. No validation is needed.

**If you're stuck:** Hint 1: Your object stores the extra value; the parent class stores the message. Hint 2: Use `self.attribute = parameter` for the channel, then call `super().__init__(...)` with only the message.

### E8 — Test a power switch without hardware (easy, ~8 min)

**Goal:** Make a supply switch that is handed its connection. Check what it sends without turning on real equipment.

**New idea:** An attribute can hold another object, so a method can ask that object to do work. A **driver** is code that turns station actions into instrument commands; a **link** carries those commands. A **fake** is a small replacement used in a test: the supplied `FakeLink` records every `send(command)` in its `sent` list. This is how a driver is tested without hardware: give it a fake, call the driver, then check the recorded commands.

```python
class StationNote:
    def __init__(self, notes: list[str]) -> None:
        self.notes = notes
    def mark_ready(self) -> None:
        self.notes.append("ready")
notes: list[str] = []
StationNote(notes).mark_ready()
print(notes)  # ["ready"]
```

In E8, `self.link.send(...)` means: find this switch's link, then call that link's `send` method. `OUTP` means output in the supply's command language; `1` enables output and `0` disables it. The command is text, including its single space.

**Signature:** In `PowerSwitch`: `def __init__(self, link: FakeLink) -> None:`, `def turn_on(self) -> None:`, and `def turn_off(self) -> None:`

**Examples:**

```python
link = FakeLink()
switch = PowerSwitch(link)  # link.sent is []
switch.turn_on()  # None; link.sent is ["OUTP 1"]
switch.turn_off()  # None; link.sent is ["OUTP 1", "OUTP 0"]
switch.turn_off()  # None; link.sent is ["OUTP 1", "OUTP 0", "OUTP 0"]
```

**Contract:** Store the exact supplied link as `self.link`; creating the switch sends nothing. Every `turn_on()` calls its `send("OUTP 1")` once, and every `turn_off()` calls its `send("OUTP 0")` once, in call order. Both methods return `None`; leave `FakeLink` unchanged.

**If you're stuck:** Hint 1: The caller already made the link; the switch only needs to remember it. Hint 2: Store the parameter on `self`, then call `self.link.send(...)` with the appropriate command text.

Next, [d19](../d19/README.md) goes one step further: the link also answers **queries**, commands that return reply text, and a fake stores scripted replies in a dictionary. A **protocol** describes the methods a link must offer, so a fake and a real connection can both work with the same driver.

### E9 — Let a dataclass store the fields (easy, ~6 min)

**Goal:** Make a second version of E1's reading with the same `name` and `value`. Let Python write the setup method.

**New idea:** A **dataclass** generates common methods from declared **fields**, the attributes listed in the class. A **decorator** is an `@` line above a class or function that changes how it is created; `@dataclass` generates `__init__` and field-by-field equality. The starter already imports `dataclass`; `from ... import ...` makes a named tool available. Delete the whole placeholder `DataReading.__init__` method, including its `def`, docstring and `raise`, then declare the two fields and add the decorator above `class DataReading`.

```python
from dataclasses import dataclass
@dataclass
class BenchLabel:
    station: str
    operator: str
label = BenchLabel("north", "Sam")
print(label.station)  # north
```

**Signature:** Generated for `DataReading`: `def __init__(self, name: str, value: float) -> None:`. Do not write this method yourself; declare `name: str` and `value: float` inside the decorated class instead.

**Examples:**

```python
DataReading("supply", 5.0).name  # "supply"
DataReading("load", 0.2).value  # 0.2
DataReading("supply", 5.0) == DataReading("supply", 5.0)  # True
```

**Contract:** Make `DataReading` a dataclass with `name: str` followed by `value: float`, both required inputs. Store both values unchanged; do not add validation or a `within` method. Keep the original `Reading` class for E10.

**If you're stuck:** Hint 1: You are replacing handwritten setup with fields, not filling in the old setup method. Hint 2: Follow `BenchLabel`'s shape: `@dataclass`, the class header, then two indented field declarations.

Next, [d06](../d06/README.md) adds **enums**, classes with named choices, and **frozen dataclasses**, records whose fields cannot be reassigned. It validates those records in `__post_init__`, a method run after generated setup, and returns new records for conversions. It also works with **generators**, which supply items as needed and can be read through only once.

### E10 — Count passing reading objects (easy, ~7 min)

**Goal:** Count how many readings in a station batch pass the same limits. Use the original `Reading` class from E1 and E2.

**New idea:** Combine the loop from the syntax refresher with E2's method call and E3's read-add-store counter pattern. A list can hold reading objects, and `if` selects which items increase the counter.

```python
def count_ready(flags: list[bool]) -> int:
    total = 0
    for flag in flags:
        if flag:
            total = total + 1
    return total
print(count_ready([True, False, True]))  # 2
```

**Signature:** `def count_passing(readings: list[Reading], low: float, high: float) -> int:`

**Examples:**

```python
count_passing([Reading("a", 5.0), Reading("b", 6.0)], 4.5, 5.5)  # 1
count_passing([Reading("a", 4.5), Reading("b", 5.5)], 4.5, 5.5)  # 2
count_passing([], 4.5, 5.5)  # 0
```

**Contract:** Count each reading whose `within(low, high)` returns `True`, including repeated readings. Return `0` for an empty list. Leave the objects and list unchanged.

**If you're stuck:** Hint 1: The counter belongs to this call; each item already knows how to check its value. Hint 2: Use `for reading in readings:`, then an `if` with `reading.within(...)`, and return the counter after the loop.

### E11 — Read three object mistakes (QUIZ, easy, ~5 min)

**Goal:** Help an operator understand three bugs in station classes. Return your chosen option letters instead of fixing the snippets below.

**New idea:** Read a method definition, the attribute spelling, and the call separately to find where the code goes wrong. An **`AttributeError`** means an object does not have the attribute you asked for; a **`TypeError`** can mean a call supplied the wrong number of inputs. A **dictionary** pairs keys with values; `{}` encloses it, `:` separates a key from its value, and commas separate pairs. `dict[str, str]` means text keys and text values; this unrelated example returns station roles, not quiz answers.

```python
def station_roles() -> dict[str, str]:
    return {"bench": "measure", "desk": "review"}
roles = station_roles()
print(roles["bench"])  # measure
```

Here `roles["bench"]` uses square brackets to look up the value for a dictionary key.

**Signature:** `def object_answers() -> dict[str, str]:`

**Examples:**

```python
len(object_answers())  # 3
object_answers().get("Q4")  # None
```

`len(...)` counts dictionary entries. `.get(key)` reads a dictionary value; it returns `None` if the key is missing. These calls show the answer format without giving away letters; each question has exactly one correct option.

Q1. This station helper forgot something. What happens at the last line?

```python
class Station:
    def ready() -> bool:
        return True
station = Station()
station.ready()
```

- A. It returns `True` because `ready` takes no written inputs.
- B. It raises `TypeError`: Python supplies the instance, but the definition forgot `self`.
- C. It raises `ValueError` because the station has no name.

Q2. What explains the error at the last line?

```python
class Probe:
    def __init__(self, name: str) -> None:
        self.name = name
probe = Probe("voltage")
probe.nmae
```

- A. The constructor must return `name` before any attribute can be read.
- B. Attribute names can only have one letter.
- C. It raises `AttributeError` because `nmae` is not the stored attribute `name`.

Q3. What happens to `clicks` here?

```python
class Button:
    def __init__(self) -> None:
        self.clicks = 0
    def click(self) -> None:
        self.clicks = self.clicks + 1
button = Button()
button.click
```

- A. It stays `0`: `button.click` refers to the method; `button.click()` would run it.
- B. It becomes `1` because looking up a method runs it.
- C. It becomes `None` because the method has no `return`.

**Contract:** Return a dictionary with exactly the keys `"Q1"`, `"Q2"`, and `"Q3"`, each mapped to one uppercase option letter (`"A"`, `"B"`, or `"C"`). Return letters, not explanations; do not print them or run the broken snippets inside your answer function.

**If you're stuck:** Hint 1: Revisit E1 for automatic `self`, E2 for stored attribute names, and E6 for method parentheses. Hint 2: Use `return {"Q1": "...", "Q2": "...", "Q3": "..."}` with your chosen letters in place of the dots.
