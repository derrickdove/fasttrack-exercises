# p02 — Decisions and loops

**Time:** about 60 minutes · **Read first:** the p02 Read first page in your tracker. Optional lookup: [Automate the Boring Stuff 2e chapter 2, flow control](https://automatetheboringstuff.com/2e/chapter2/) · **You edit:** `starter/decisions.py`

## What you're building

A **test station** is a computer connected to equipment that checks hardware. A **reading** is one measured value. A **limit** is an allowed boundary for that value. You will make small decisions about readings, then repeat those decisions over a list.

This set prepares you for [d02: decisions, loops and functions](../d02/README.md). Here every limit is a number. Later, d02 adds missing limits, positions in lists, and several good readings in a row.

## How this works

1. Open `starter/decisions.py` in VS Code. Replace each `raise NotImplementedError(...)` with your code. A **NotImplementedError** marks an unfinished exercise. Leave the function names and type hints in place. Do not edit `tests/`.
2. Save, then run `bash tools/run.sh p02` from the repository folder. This is a **shell command**, an instruction for the terminal. Type Python code in the file, not at the Bash prompt. Do not type `>>>`; that is a prompt shown in some Python books.
3. At first the report says `Exercises: 0 / 11 passed`. Rerun after each exercise. A **test** calls your function and checks its result. Each exercise may have several tests; all must pass for that exercise to pass.
4. Work for the minutes shown, then ask your coach for a hint if needed. Report **all pass / partial / stuck**, including the exercise where you stopped.

A **function** is named code you can call with inputs. Its **signature** is its first line. In `def echo(value: float) -> float:`, `def` starts the function, parentheses `()` hold the inputs, and the final `:` starts its body. The `:` after `value` introduces a **type hint**, a note about the expected kind of value; `->` introduces the result type. `float` means a number that can have a fractional part, `int` means a whole number, and `str` means text.

**Indentation** means spaces at the start of a line; it tells Python which lines belong together. Use four spaces for a function body, then four more for a block inside it. Lines at the same indentation belong to the same block.

A **variable** is a name for a value. One equals sign, `=`, stores a value under a name. Quotes such as `"PASS"` mark text. Commas separate inputs or items. A **comment** starts with `#` and explains code without running.

`return` sends a result back to the caller and ends that function call. `print(...)` only displays a value; the tests need a returned result. Run worked examples in a separate scratch file if you want to try them; keep extra calls out of the starter file.

All inputs have the shown types. Numbers are ordinary finite numbers. When both limits appear, `low` is no greater than `high`. Leave the supplied lists unchanged. Only E10 asks you to reject an input. No real equipment is needed.

## Exercises

### E1 — Is the reading too high? (~4 min)

**Goal:** Tell the station whether a reading is over its upper limit.

**New idea:** A **comparison** checks how two values relate. It gives a **Boolean**, either `True` or `False`; its type hint is `bool`. The symbol `>` means greater than, `==` means equal to, and `!=` means not equal to. Equality does not count as greater than.

```python
def has_spare_slots(slots: int) -> bool:
    return slots > 0

print(has_spare_slots(2))  # True
```

**Signature:** `def is_over_limit(reading: float, limit: float) -> bool:`

**Examples:**

```python
is_over_limit(6.0, 5.0)  # True
is_over_limit(5.0, 5.0)  # False
is_over_limit(4.0, 5.0)  # False
```

**Contract:** Return `True` only when `reading` is greater than `limit`. Return the Boolean itself, not the text `"True"` or `"False"`.

**If you're stuck:**

1. A comparison already produces the kind of result you need.
2. Use the line shape `return left > right`, with the input names from the signature.

### E2 — Give the operator a result (~4 min)

**Goal:** Give the operator, the person running the station, a `"PASS"` or `"FAIL"` message for one reading.

**New idea:** An **if / else** chooses between two blocks of code. A **condition** is an expression that gives `True` or `False`; the `if` block runs when it is true, and `else` runs otherwise. Put a colon after the condition and after `else`, and indent their bodies.

```python
def tray_message(items: int) -> str:
    if items == 0:
        return "EMPTY"
    else:
        return "LOADED"

print(tray_message(0))  # EMPTY
```

**Signature:** `def pass_or_fail(reading: float, limit: float) -> str:`

**Examples:**

```python
pass_or_fail(6.0, 5.0)  # "FAIL"
pass_or_fail(5.0, 5.0)  # "PASS"
pass_or_fail(4.0, 5.0)  # "PASS"
```

**Contract:** Return `"FAIL"` when the reading is greater than the limit; otherwise return `"PASS"`. Use exactly these uppercase strings.

**If you're stuck:**

1. The decision is the same comparison as E1, but the result is now text.
2. Use `if reading > limit:` and an `else:` block, each with its own `return`.

### E3 — Low, OK, or high? (~5 min)

**Goal:** Classify a reading using the station's lower and upper limits.

**New idea:** An **elif** means “otherwise, if” and adds another choice. Python tries the conditions from top to bottom and runs only the first matching block. A final `else` handles what is left. The symbol `<` means less than.

```python
def tray_size(items: int) -> str:
    if items == 0:
        return "EMPTY"
    elif items < 3:
        return "SMALL"
    else:
        return "LARGE"
print(tray_size(2))  # SMALL
```

**Signature:** `def reading_band(reading: float, low: float, high: float) -> str:`

**Examples:**

```python
reading_band(3.0, 4.0, 6.0)  # "LOW"
reading_band(4.0, 4.0, 6.0)  # "OK"
reading_band(7.0, 4.0, 6.0)  # "HIGH"
```

**Contract:** Return `"LOW"` below `low`, `"HIGH"` above `high`, and `"OK"` otherwise. A reading equal to either limit is `"OK"`.

**If you're stuck:**

1. There are two ways to be outside the limits; everything left is OK.
2. Start with `if reading < low:`, then use `elif` for the upper limit and `else` for the middle.

### E4 — Inside both limits (~5 min)

**Goal:** Tell the station whether a reading is inside an allowed range, including its endpoints.

**New idea:** The word **and** combines conditions and is true only when both are true. The word **or** is true when at least one condition is true. The symbols `>=` and `<=` mean greater than or equal to, and less than or equal to. An **inclusive** range accepts both endpoints.

```python
def can_run(door_closed: bool, operator_ready: bool) -> bool:
    return door_closed and operator_ready

print(can_run(True, False))  # False
print(True or False)        # True
```

**Signature:** `def is_in_range(reading: float, low: float, high: float) -> bool:`

**Examples:**

```python
is_in_range(4.0, 4.0, 6.0)  # True
is_in_range(6.0, 4.0, 6.0)  # True
is_in_range(7.0, 4.0, 6.0)  # False
```

**Contract:** Return a Boolean saying whether the reading is at least `low` and at most `high`. For practice, join two comparisons with `and`.

**If you're stuck:**

1. Being above the lower limit alone does not guarantee being below the upper limit.
2. Use the shape `return comparison_one and comparison_two`, with `>=` and `<=`.

### E5 — Add a batch of readings (~6 min)

**Goal:** Return the total of all readings collected by the station.

**New idea:** A **list** is an ordered collection; square brackets `[]` hold its items, and `list[float]` means a list of numbers. A **for loop** repeats its indented body once for each item, in order; `in` names the collection to visit. A **running total** is a variable you update after each item. The symbol `+` adds values, and `total = total + item` stores the updated total.

```python
def total_label_letters(labels: list[str]) -> int:
    total = 0
    for label in labels:
        total = total + len(label)
    return total

print(total_label_letters(["AB", "C"]))  # 3
```

`len(...)` gives the number of items in a list or characters in text. In the example, `return` lines up with `for`, so it runs after the whole loop.

**Signature:** `def total_readings(readings: list[float]) -> float:`

**Examples:**

```python
total_readings([1.5, 2.0, 0.5])  # 4.0
total_readings([3.0])            # 3.0
total_readings([])               # 0.0
```

**Contract:** Use a `for` loop and a total starting at `0.0`. Return the final total after the loop; an empty list has total `0.0`.

**If you're stuck:**

1. Before any readings, the total is zero; each reading adds to it.
2. Put `total = total + reading` inside `for reading in readings:`, then return after the loop.

### E6 — Count high readings (~5 min)

**Goal:** Count how many readings exceed one upper limit.

**New idea:** A **counter** is a variable that tracks how many items match a condition. It increases by one for each match, rather than adding the reading's value. Put an `if` inside the loop so the counter changes only for matches.

```python
def count_empty_labels(labels: list[str]) -> int:
    count = 0
    for label in labels:
        if label == "":
            count = count + 1
    return count

print(count_empty_labels(["A", "", ""]))  # 2
```

**Signature:** `def count_over_limit(readings: list[float], limit: float) -> int:`

**Examples:**

```python
count_over_limit([4.0, 7.0, 8.0], 5.0)  # 2
count_over_limit([5.0, 5.0], 5.0)       # 0
count_over_limit([], 5.0)               # 0
```

**Contract:** Use a `for` loop to count readings strictly greater than `limit`. Count repeated high readings separately; return `0` for an empty list.

**If you're stuck:**

1. This is E5's loop with a count instead of a total, and E1's comparison.
2. Start `count = 0`; inside the matching `if` block use `count = count + 1`.

### E7 — Stop at the first failure (~6 min)

**Goal:** Return the first reading over a limit so the operator can inspect its value.

**New idea:** An **early return** ends the whole function as soon as a result is known. Inside a loop, it stops the loop too. `None` is Python's value meaning “no result”; `float | None` allows a number or `None`, with `|` meaning either type. A final `return None` after the loop handles a search that found nothing.

```python
def first_loaded_tray(trays: list[int]) -> int | None:
    for items in trays:
        if items > 0:
            return items
    return None

print(first_loaded_tray([0, 4, 2]))  # 4
```

**Signature:** `def first_over_limit(readings: list[float], limit: float) -> float | None:`

**Examples:**

```python
first_over_limit([4.0, 7.0, 9.0], 5.0)  # 7.0
first_over_limit([4.0, 5.0], 5.0)       # None
first_over_limit([], 5.0)               # None
```

**Contract:** Use a `for` loop and return the first reading strictly greater than `limit`, in the supplied order. Return its value, not its position; return `None` when no reading fails, including an empty list.

**If you're stuck:**

1. Once a reading fails, you already know the answer; do not inspect later readings.
2. Put `return reading` inside the matching `if`, and `return None` outside the loop.

### E8 — Number the channels (~5 min)

**Goal:** Build a list of the station's channel numbers, starting at 1. A **channel** is one numbered connection on an instrument.

**New idea:** **range()** supplies whole numbers: `range(start, stop)` starts at `start` and stops before `stop`. `range(stop)` starts at zero; for example, `range(3)` supplies 0, 1, 2. The **append** operation adds one item to the end of a list; the dot in `numbers.append(item)` selects that list's operation. `numbers: list[int] = []` creates an empty list with a type hint for its future items.

```python
def three_trial_numbers() -> list[int]:
    trials: list[int] = []
    for number in range(10, 13):
        trials.append(number)
    return trials

print(three_trial_numbers())  # [10, 11, 12]
```

**Signature:** `def channel_numbers(n: int) -> list[int]:`

**Examples:**

```python
channel_numbers(3)  # [1, 2, 3]
channel_numbers(1)  # [1]
channel_numbers(0)  # []
```

**Contract:** The input `n` is zero or greater. Use a `for` loop with `range()` to return the numbers 1 through `n` in order; return an empty list for zero.

**If you're stuck:**

1. The stop value is left out, but the last channel must be included.
2. Use `range(1, n + 1)` and append each number to an initially empty list.

### E9 — Step up the voltage (~7 min)

**Goal:** Starting at zero volts, count the fixed voltage steps needed to reach or exceed a target. A **volt** is a unit of electrical voltage.

**New idea:** A **while loop** repeats as long as its condition is true. Python checks the condition before every turn, so the body may run zero times. Update the value used by the condition inside the loop so it can eventually stop. This combines a changing total with E6's counter.

```python
def boxes_for_items(items: int) -> int:
    capacity = 0
    boxes = 0
    while capacity < items:
        capacity = capacity + 4
        boxes = boxes + 1
    return boxes
print(boxes_for_items(9))  # 3
```

**Signature:** `def steps_to_target(target: float, step: float) -> int:`

**Examples:**

```python
steps_to_target(2.0, 0.5)  # 4
steps_to_target(2.5, 1.0)  # 3
steps_to_target(0.0, 0.5)  # 0
```

**Contract:** `target` is zero or greater and `step` is positive; supplied voltages use whole volts, halves, or quarters. Use a `while` loop, starting at `0.0` volts, adding `step` each time until the voltage is at least `target`. Return the number of steps, even when the last step goes past the target.

**If you're stuck:**

1. Track two things: the voltage reached so far and the number of steps taken.
2. Use `while voltage < target:`; inside it update both voltage and count, then return the count after the loop.

### E10 — Reject a negative channel count (~5 min)

**Goal:** Stop a negative count before the station builds a channel list. Reuse E8 for valid counts.

**New idea:** A **guard** checks for an unacceptable input before doing the normal work. **ValueError** is Python's error for an unacceptable value; `raise ValueError("message")` stops the call with that error. Unlike returning a result, raising an error tells the caller the request cannot be completed. After the guard, you can call your earlier function and return its result.

```python
def checked_total(parts: int, spares: int) -> int:
    if spares < 0:
        raise ValueError("spares must be zero or greater")
    return parts + spares

print(checked_total(3, 2))  # 5
```

**Signature:** `def checked_channel_numbers(count: int) -> list[int]:`

**Examples:**

```python
checked_channel_numbers(2)   # [1, 2]
checked_channel_numbers(0)   # []
checked_channel_numbers(-1)  # raises ValueError
```

**Contract:** Raise `ValueError` when `count` is negative; the message is your choice. Otherwise return the same channel list as `channel_numbers(count)` from E8; calling that function is encouraged.

**If you're stuck:**

1. Check the unacceptable case first, then keep the normal path simple.
2. Start with `if count < 0:` and an indented `raise ValueError(...)`, then return E8's result after the guard.

### E11 — Spot three bugs (QUIZ, ~8 min)

**Goal:** Read three short station programs and identify why they do not do what the operator expects.

**New idea:** A **bug** is a mistake in a program; this quiz combines comparisons, ranges, and return placement from earlier exercises. A **dictionary** pairs named keys with values: `dict[str, str]` means text keys and text values, braces `{}` enclose the pairs, and `:` separates each key from its value. Return a dictionary mapping question names to your chosen uppercase option letters, like this unrelated shape quiz. `len(answers)` counts its entries, and `list(answers)` makes a list of its keys in their written order.

```python
def shape_answers() -> dict[str, str]:
    return {"S1": "B", "S2": "A"}

print(shape_answers())  # {'S1': 'B', 'S2': 'A'}
```

**Signature:** `def bug_answers() -> dict[str, str]:`

**Examples:** These show the answer format without giving away the letters.

```python
len(bug_answers())   # 3
list(bug_answers())  # ["Q1", "Q2", "Q3"] (write the keys in this order)
```

**Q1.** The station should accept the text `"RUN"`. Python cannot load this code. Which change fixes the comparison?

```python
def mode_ready(mode: str) -> bool:
    if mode = "RUN":
        return True
    return False
```

- A. Add `print(mode)` before the `if`.
- B. Replace `"RUN"` with `True`.
- C. Replace `=` with `==` in the `if` line.

**Q2.** The station needs channels 1 through 3, but this call returns `[1, 2]`. Which change includes the final channel?

```python
def selected_channels(n: int) -> list[int]:
    channels: list[int] = []
    for number in range(1, n):
        channels.append(number)
    return channels
```

- A. Use `range(1, n + 1)`.
- B. Start the range at zero.
- C. Put `return channels` inside the loop.

**Q3.** The operator calls `batch_total([2.0, 3.0])`, expecting `5.0`, but gets `2.0`. Which change makes it add every reading?

```python
def batch_total(readings: list[float]) -> float:
    total = 0.0
    for reading in readings:
        total = total + reading
        return total
```

- A. Start `total` at `1.0`.
- B. Move `return total` left by four spaces so it runs after the loop.
- C. Replace `return total` with `print(total)` at the same indentation.

**Contract:** Return exactly the keys `"Q1"`, `"Q2"`, and `"Q3"` in that order, each mapped to one of `"A"`, `"B"`, or `"C"`. Choose one letter per question; do not edit or run the broken snippets to submit your answers.

**If you're stuck:**

1. Reread E1 for comparison symbols, E8 for the excluded stop, and E5 for return placement.
2. Use the shape `return {"Q1": "letter", "Q2": "letter", "Q3": "letter"}`, replacing each `letter` with your choice.

## Next: d02

In [d02](../d02/README.md), a limit may be `None`, meaning "no limit on that side". Check `limit is not None` before comparing a number with it; `is not None` checks that a value is present. A limit of zero is still a real limit.

```python
def shelf_too_full(books: int, limit: int | None) -> bool:
    if limit is not None:
        return books > limit
    return False
print(shelf_too_full(4, None))  # False
print(shelf_too_full(4, 3))     # True
```
