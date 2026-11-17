# p03 — Lists and dictionaries

**Time:** about 63 minutes · **Read first:** the p03 Read first page in your tracker. Optional lookup: [Automate the Boring Stuff 2e chapter 4: lists](https://automatetheboringstuff.com/2e/chapter4/) and [chapter 5: dictionaries](https://automatetheboringstuff.com/2e/chapter5/) · **You edit:** `starter/collections_basics.py`

## What you're building

A **test station** is a computer and equipment used to check hardware. An **instrument** takes measurements; a **reading** is one measured number. A **channel** is one measurement connection. You will collect readings, find channel information, and prepare small reports for an **operator**, the person running the station. No equipment is needed.

## How this works

1. Edit `sets/p03/starter/collections_basics.py`. Replace each `raise NotImplementedError(...)` line with your code. This line marks unfinished work; leave `tests/` alone.
2. Save, then run `bash tools/run.sh p03` in the terminal from the repository folder. A **terminal** is where you type shell commands. Put Python code in the file, not at the shell prompt, and never type the interactive Python prompt `>>>` into your file.
3. At first the report says `Exercises: 0 / 12 passed`. Rerun after each exercise. Several checks may belong to one exercise; all must pass. Report **all pass / partial / stuck** in the tracker at 63 minutes.

A **function** is named code that takes inputs and sends a result back with `return`. `print(...)` only displays something; it does not send the result back to a test. The examples below use `print` to show results, but your functions must return their results.

A **signature** is the `def` line naming a function and its inputs. **Type hints** describe the inputs and result: `str` means text, `int` means whole number, and `float` means a number that may have a fractional part. In a signature, `:` introduces an input's type, `->` introduces the result type, and the final `:` starts the function body. **Indentation** means spaces at the start of a line; use four spaces inside a function and four more inside each loop or `if`.

In code, `=` gives a name a value; `==` compares two values for equality. Quotes surround text, commas separate items or inputs, and `()` holds a function's inputs; empty `()` means no inputs. A **comment** starts with `#` and is a note Python ignores. In examples, `#` shows the expected displayed result. Keep matching brackets: `[` closes with `]`, never `}`.

Inputs have the stated types and are valid. Do not add input checks. Leave every input collection unchanged. An **empty** collection has no items. Where empty inputs are allowed, their results are stated. Work in order; later exercises reuse earlier tools.

## Exercises

### E1 — Collect three readings (easy, ~4 min)

**Goal:** Put three instrument readings into a list in the order they arrived.

**New idea:** A **list** is an ordered collection that can change; `[]` makes an empty list and `[2, 5]` makes a list with two items. `list[float]` in a type hint means a list of numbers. The **append** operation, written `.append(item)`, adds one item at the end; the dot selects an operation belonging to that list. Append on its own line, then return the list, because `append` itself returns `None`, Python's value meaning no result.

```python
tools = []
tools.append("meter")
tools.append("probe")
print(tools)  # ['meter', 'probe']
```

**Signature:** `def make_readings(first: float, second: float, third: float) -> list[float]:`

**Examples:**

```python
make_readings(1.0, 2.0, 3.0)  # [1.0, 2.0, 3.0]
make_readings(0.0, 0.0, 4.5)  # [0.0, 0.0, 4.5]
```

**Contract:** Start with an empty list and use `append` to add the three readings in input order. Return that new list, keeping repeated readings.

**If you're stuck:** Hint 1: Each reading becomes one item, even if two readings are equal. Hint 2: Start with `readings: list[float] = []`, use `.append(...)` once per input, and return the list name.

### E2 — Find the last reading and the count (easy, ~5 min)

**Goal:** Help the operator find the latest reading and how many readings were collected. Write two small functions.

**New idea:** An **index** is an item's position: `items[0]` selects the first item, since positions start at zero. A **negative index** counts from the end; `items[-1]` selects the last item. `len(items)` returns the number of items, rather than any particular item. Square brackets select an item in code; they describe item types in hints such as `list[float]`.

```python
tools = ["meter", "probe", "supply"]
latest = tools[-1]
count = len(tools)
print(latest)  # supply
print(count)  # 3
```

**Signature:**

```python
def last_reading(values: list[float]) -> float:
def reading_count(values: list[float]) -> int:
```

**Examples:**

```python
last_reading([2.5, 4.0, 3.0])  # 3.0
reading_count([2.5, 4.0, 3.0])  # 3
reading_count([])  # 0
```

**Contract:** `last_reading` receives a nonempty list and returns its last item. `reading_count` returns the number of items, including zero for an empty list.

**If you're stuck:** Hint 1: A position and a count answer different questions. Hint 2: Use `values[-1]` in one function and `len(values)` in the other.

### E3 — Keep readings above a limit (easy, ~6 min)

**Goal:** Build a list containing only readings above the station's limit, an allowed boundary.

**New idea:** A **loop** repeats code; `for item in items:` visits each item in order. A **condition** is a true-or-false check, and `if condition:` runs its indented code only when the condition is true. The symbol `>` means strictly greater than, so equal values do not pass this check. **Filtering** means building a new collection containing only items that pass a check.

```python
words = ["on", "ready", "go", "probe"]
long_words = []
for word in words:
    if len(word) > 3:
        long_words.append(word)
print(long_words)  # ['ready', 'probe']
```

**Signature:** `def readings_above(values: list[float], limit: float) -> list[float]:`

**Examples:**

```python
readings_above([4.0, 5.0, 6.0, 6.0], 5.0)  # [6.0, 6.0]
readings_above([1.0, 2.0], 3.0)  # []
readings_above([], 5.0)  # []
```

**Contract:** Return a new list of readings strictly greater than `limit`. Keep their original order and repetitions; return `[]` if no readings qualify.

**If you're stuck:** Hint 1: Add to a separate list, not the list you are visiting. Hint 2: Put `if value > limit:` inside a `for` loop, then put `.append(...)` inside the `if`; return after the loop finishes.

### E4 — Use Python's list tools (easy, ~5 min)

**Goal:** Give the operator the smallest, largest, and total readings. Write three small functions.

**New idea:** A **built-in** is a tool Python supplies without an import: `min` finds the smallest item, `max` the largest, and `sum` adds all items. These tools visit the list's items for you. Each function needs just one of these tools.

```python
box_counts = [6, 2, 4]
print(min(box_counts))  # 2
print(max(box_counts))  # 6
print(sum(box_counts))  # 12
```

**Signature:**

```python
def smallest_reading(values: list[float]) -> float:
def largest_reading(values: list[float]) -> float:
def total_readings(values: list[float]) -> float:
```

**Examples:**

```python
smallest_reading([3.0, 1.0, 2.0])  # 1.0
largest_reading([3.0, 1.0, 2.0])  # 3.0
total_readings([3.0, 1.0, 2.0])  # 6.0
```

**Contract:** Every input here is nonempty. Each function returns the result named above, including every reading and its repetitions.

**If you're stuck:** Hint 1: These tools already visit the list's items for you. Hint 2: Return the result of `min`, `max`, or `sum`, as the function's name requires.

### E5 — Combine a total and a count (combine, easy, ~4 min)

**Goal:** Give the operator the average reading for a nonempty list.

**New idea:** Combine E4's total with E2's count. The **average**, also called the mean, is the total divided by the count; `/` means division. Use the whole list and leave the result unrounded.

```python
box_counts = [6, 2, 4]
total = sum(box_counts)
count = len(box_counts)
print(total / count)  # 4.0
```

**Signature:** `def average_reading(values: list[float]) -> float:`

**Examples:**

```python
average_reading([2.0, 5.0])  # 3.5
average_reading([4.5])  # 4.5
```

**Contract:** The input is nonempty. Include every reading, including repetitions, and return the average without rounding.

**If you're stuck:** Hint 1: Find both the total and the number of readings. Hint 2: Use `sum` and `len`, then divide the total by the count.

### E6 — Look up a channel's status (easy, ~5 min)

**Goal:** Find the status saved for a channel name. Return `"UNKNOWN"` when the station has no entry for that name.

**New idea:** A **dictionary** stores values under unique **keys**, the names used to look them up; `{}` makes an empty dictionary. In `{"meter": "ready"}`, braces hold the dictionary and `:` separates a key from its value; `dict[str, str]` means text keys and text values. A **lookup** such as `labels["meter"]` gets the value for that key. A **membership check** such as `"meter" in labels` asks whether the key exists; check first so a missing key does not cause an error.

```python
drawer = {"probe": "top", "cable": "bottom"}
item = "clip"
if item in drawer:
    print(drawer[item])
else:
    print("not stored")  # not stored
```

`else:` runs its indented code when the `if` check is false.

**Signature:** `def lookup_status(statuses: dict[str, str], name: str) -> str:`

**Examples:**

```python
lookup_status({"BUS_V": "READY"}, "BUS_V")  # 'READY'
lookup_status({"BUS_V": "READY"}, "TEMP_C")  # 'UNKNOWN'
lookup_status({}, "BUS_V")  # 'UNKNOWN'
```

**Contract:** Check whether `name` is a key before looking up its value. Return the saved status if present, or exactly `"UNKNOWN"` if absent. Names match exactly as written.

**If you're stuck:** Hint 1: A dictionary's `in` check checks its keys, not its values. Hint 2: Use `if name in statuses:` before using square brackets for the lookup.

### E7 — Count each status (easy, ~7 min)

**Goal:** Count how many times each status appears in the station log.

**New idea:** A **dictionary update** sets a key's value with `counts[key] = value`; this adds a new key or replaces its old value. On a key's first visit, store `1`; on later visits, add one to its saved count. The `+` symbol adds numbers, so `counts[key] + 1` is one more than its current count. `dict[str, int]` means text keys paired with whole-number counts.

```python
counts = {}
for tool in ["probe", "cable", "probe"]:
    if tool in counts:
        counts[tool] = counts[tool] + 1
    else:
        counts[tool] = 1
print(counts)  # {'probe': 2, 'cable': 1}
```

**Signature:** `def count_statuses(statuses: list[str]) -> dict[str, int]:`

**Examples:**

```python
count_statuses(["PASS", "FAIL", "PASS"])  # {'PASS': 2, 'FAIL': 1}
count_statuses(["READY", "READY"])  # {'READY': 2}
count_statuses([])  # {}
```

**Contract:** Return a new dictionary with one key for each status that appears and its occurrence count as the value. Do not include statuses that never appear; empty input returns `{}`.

**If you're stuck:** Hint 1: Keep one count per status, not one total for the whole log. Hint 2: Start with `counts: dict[str, int] = {}` and use an `if status in counts:` branch to choose between adding one and starting at one.

### E8 — Find channel names over the limit (easy, ~6 min)

**Goal:** The station has one reading per named channel and one shared limit. Return the names whose readings exceed that limit.

**New idea:** The dictionary operation **items** supplies each key together with its value. The loop shape `for name, value in mapping.items():` gives you both parts on each visit; the comma separates the two receiving names. Dictionaries visit keys in **insertion order**, the order in which the entries were added. Combine this loop with E3's filtering idea to collect names rather than readings.

```python
stock = {"probe": 2, "cable": 8, "clip": 1}
low_stock = []
for tool, count in stock.items():
    if count < 3:
        low_stock.append(tool)
print(low_stock)  # ['probe', 'clip']
```

Here `<` means strictly less than.

**Signature:** `def channels_over_limit(readings: dict[str, float], limit: float) -> list[str]:`

**Examples:**

```python
channels_over_limit({"TEMP_C": 6.0, "BUS_V": 5.0, "AUX_V": 7.0}, 5.0)  # ['TEMP_C', 'AUX_V']
channels_over_limit({"BUS_V": 5.0}, 5.0)  # []
channels_over_limit({}, 5.0)  # []
```

**Contract:** Return a new list of keys whose values are strictly greater than `limit`; equality does not qualify. Keep dictionary insertion order, without sorting. Return `[]` when no names qualify.

**If you're stuck:** Hint 1: Compare the reading, but collect the name. Hint 2: Use `for name, value in readings.items():` and put your comparison inside that loop.

### E9 — Read a field from every record (easy, ~5 min)

**Goal:** Each station record contains a channel name and status. Make a list of the channel names.

**New idea:** A **record** is a dictionary describing one thing, and a **field** is one named part of that record. A list of dictionaries holds several such records; `list[dict[str, str]]` means a list of dictionaries with text keys and text values. Loop through the outer list, then look up the same field in each record. You need only one loop.

```python
tools = [{"kind": "probe", "shelf": "A"}, {"kind": "cable", "shelf": "B"}]
shelves = []
for tool in tools:
    shelves.append(tool["shelf"])
print(shelves)  # ['A', 'B']
```

**Signature:** `def record_channels(records: list[dict[str, str]]) -> list[str]:`

**Examples:**

```python
record_channels([{"channel": "BUS_V", "status": "PASS"}, {"channel": "TEMP_C", "status": "FAIL"}])  # ['BUS_V', 'TEMP_C']
record_channels([{"channel": "BUS_V"}, {"channel": "BUS_V"}])  # ['BUS_V', 'BUS_V']
record_channels([])  # []
```

**Contract:** Every record contains `"channel"`; ignore any other fields. Return a new list of those channel values in record order, including repetitions. Empty input returns `[]`.

**If you're stuck:** Hint 1: The loop's current item is a dictionary, not a channel name. Hint 2: Look up `record["channel"]` and append that value to your result list.

### E10 — Sort a copy, keep the original (easy, ~7 min)

**Goal:** Return readings or integer channel numbers in ascending order while leaving their recorded order untouched. Write two small functions.

**New idea:** `sorted(items)` returns a new list in **ascending order**, from smallest to largest, and leaves the input unchanged. An **alias** is a second name for the very same list; assigning `other = original` does not copy it. A **copy** is a separate list; `.copy()` creates one, and changes to that list's items do not change the original integer list. `.sort()` changes the list it belongs to and returns `None`, so `sorted(...)` is the direct way to get a sorted copy.

```text
other = original:        original ----> [3, 1]
                        other -------^          one list
other = original.copy(): original ----> [3, 1]
                         other ------> [3, 1]    two lists
```

```python
tools = ["probe", "cable"]
alias = tools
alias.append("clip")
copy = sorted(tools)
print(tools)  # ['probe', 'cable', 'clip']
print(copy)  # ['cable', 'clip', 'probe']
```

**Signature:**

```python
def ascending_readings(values: list[float]) -> list[float]:
def sorted_channels(channels: list[int]) -> list[int]:
```

**Examples:**

```python
sorted_channels([3, 1, 3, 2])  # [1, 2, 3, 3]; input stays [3, 1, 3, 2]
ascending_readings([3.0, 1.0, 2.0])  # [1.0, 2.0, 3.0]; input stays unchanged
sorted_channels([])  # []; still a separate new list
```

**Contract:** Each function returns a new list of all its input items in ascending order, keeping repetitions. `ascending_readings` receives a nonempty list; `sorted_channels` also allows empty input. Leave the input unchanged, even when it is already sorted or empty.

**If you're stuck:** Hint 1: Two names pointing at one list do not protect the original order. Hint 2: Use `sorted(...)`, or call `.copy()` before `.sort()` and then return the copy; do not return `.sort()`'s result.

### E11 — List each channel once (easy, ~4 min)

**Goal:** The station may record the same integer channel number several times. Return each channel number once, in ascending order.

**New idea:** A **set** is a collection that keeps each distinct item only once. `set(items)` removes repetitions, but does not promise ascending order. Combine it with the list tool `sorted(...)` to get an ordered list. This reuses E10's new-list idea while removing repetitions too.

```python
box_sizes = [8, 2, 8, 4, 2]
distinct = set(box_sizes)
ordered = sorted(distinct)
print(ordered)  # [2, 4, 8]
```

**Signature:** `def unique_channels(channels: list[int]) -> list[int]:`

**Examples:**

```python
unique_channels([3, 1, 3, 2, 1])  # [1, 2, 3]
unique_channels([4, 4, 4])  # [4]
unique_channels([])  # []
```

**Contract:** Return a new list of distinct channel numbers in ascending order. Leave the input unchanged; empty input returns `[]`.

**If you're stuck:** Hint 1: Removing repetitions and ordering are two separate jobs. Hint 2: First use `set(...)`, then use `sorted(...)` on that set.

### E12 — Read the error and choose a fix (QUIZ, easy, ~5 min)

**Goal:** Help an operator repair three collection mistakes. Return your chosen option letters in a dictionary.

**New idea:** A **traceback** shows where Python stopped; its final line names the error and explains the problem. A **KeyError** means a dictionary key was missing, and an **IndexError** means a list position was missing. A **TypeError** means an operation was used with unsuitable types, such as comparing a whole list to a number. Use E2's count and index tools and E6's key check to choose a fix; the snippets below are for reading, not for pasting into the starter.

```python
drawer = {"cable": "B"}
item = "probe"
if item in drawer:
    print(drawer[item])
else:
    print("no shelf")  # no shelf: the missing key is checked first
```

**Signature:** `def collection_answers() -> dict[str, str]:`

**Examples:**

```python
sorted(collection_answers())  # ['Q1', 'Q2', 'Q3']; lists keys, not answers
len(collection_answers())  # 3
```

Choose one option per question. `True` and `False` are Python's two truth values. The symbol `>=` means greater than or equal to.

**Q1.** This channel was not recorded. Which replacement returns its status when present and `"UNKNOWN"` otherwise?

```python
statuses = {"BUS_V": "READY"}
name = "TEMP_C"
print(statuses[name])
```

```text
KeyError: 'TEMP_C'
```

- A. Look up `statuses[0]` instead.
- B. Check `if name in statuses:` before the lookup, and use `"UNKNOWN"` in the `else` branch.
- C. Put `print(statuses[name])` inside another `print(...)`.

**Q2.** The list is nonempty. Which replacement gets its last reading, whatever its length?

```python
values = [2.0, 4.0]
print(values[2])
```

```text
IndexError: list index out of range
```

- A. Use `values[len(values)]`.
- B. Use `values[0]`, since the first item is always the last item.
- C. Use `values[-1]`.

**Q3.** The operator wants to know whether at least three readings were collected. Which replacement checks the count?

```python
readings = [1.0, 2.0, 3.0]
print(readings >= 3)
```

```text
TypeError: '>=' not supported between instances of 'list' and 'int'
```

- A. Use `len(readings) >= 3`.
- B. Use `readings[-1] >= 3`, since the last value always equals the count.
- C. Use `readings == 3`.

**Contract:** Return a dictionary with exactly the keys `"Q1"`, `"Q2"`, and `"Q3"` and their chosen uppercase letters `"A"`, `"B"`, or `"C"`. Return letters, not the option text; do not run the broken snippets inside your function.

**If you're stuck:** Hint 1: Read the final error line, then decide whether the code needs a key, a position, or a count. Hint 2: Reread E6 for Q1 and E2 for Q2 and Q3; use a dictionary literal shaped like `{"question": "letter"}` for your answers.

After this set, try [d03 — Channels and readings: collections](../d03/README.md). It combines these tools to group readings, find missing channels, and check station command sequences.

When a dictionary groups items into lists, give each key its **own new list**. Create that list inside the loop when the key is first seen, then append to the list stored under that key. Do not create one list outside the loop and share it between keys: appending through either key would change that same list.

```python
by_initial = {}
for word in ["pen", "cup", "pad"]:
    initial = word[0]
    if initial not in by_initial:
        by_initial[initial] = []
    by_initial[initial].append(word)
print(by_initial)  # {'p': ['pen', 'pad'], 'c': ['cup']}
```

Here `not in` means the key is absent; the `p` and `c` keys each receive a separate list. d03 also uses **tuples**, fixed sequences of values, which its reading covers.
