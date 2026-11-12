# t01 — Think it through: questions first, then simulate

**Time:** about 45 minutes (5 minutes of questions and tracing, then 40 minutes for five exercises) · **Read first:** No new reading. Reread the READMEs of [sets/p02 (loops)](../p02/README.md) and [sets/p03 (lists and dictionaries)](../p03/README.md) if needed. · **You edit:** `starter/stage.py`

## What you're building

A **probe head** is the part that touches a device to take a measurement. An **XY positioning stage** moves that head left/right and up/down across a flat surface at a test station. You will simulate its motion: track numbers in Python without moving real equipment. This is interview practice, rather than preparation for one particular set.

Here is the deliberately vague interview task: "A head repeats a string of commands forever on an infinite flat grid. L turns left, R turns right, and F moves forward. Is the command string valid?"

### Before E1 (5 min): write your own questions

Before reading the agreed rules below, write three questions you would ask about the vague task. Say them to your coach. Use the same five minutes for the two paper traces below.

### Agreed rules

For this exercise, **valid** means the repeating route stays **bounded**: it does not drift farther and farther away. It will return to its starting position after some whole passes through the string. A passing visit to the start followed by endless drift does not count. For example, FLLFLLF touches the start during its first pass but ends each pass one step farther north. We compare position only; the **heading**, the direction the head faces, need not match when it first returns.

Agreed rules for E2 onward: L and R turn exactly 90 degrees without moving; F moves one grid step. Only uppercase L, R and F are accepted. The empty string is accepted and valid: the head stays at the start. There is no fixed length limit; inputs are finite strings, and efficient handling of long strings matters. There are no walls or obstacles, and the head starts at `(0, 0)` facing north. North increases y; east increases x. South and west decrease them.

## How this works

Spend the first 5 minutes writing questions and tracing the two cases, then work through the five exercises (40 minutes).

1. Replace each `raise NotImplementedError(...)` in `starter/stage.py`. This error marks unfinished code. Leave `tests/` alone. The two quizzes also use functions: return a dictionary of chosen letters.
2. Save and run `bash tools/run.sh t01` in the terminal from the exercises repo. Initially you should see `Exercises: 0 / 5 passed`. Rerun after each exercise. **pytest** is the tool running these checks; one exercise may contain several checks.
3. Report **all pass / partial / stuck** in the tracker. Stop at 45 minutes and report where you reached. Ask your coach for a hint if needed.

Type Python in the file, then save it; type the Bash command above in the terminal. Do not type a `>>>` prompt. Use `return` to send a value to a caller; `print` only displays it. A missing `return` gives `None`, meaning no returned value.

A **signature** is the function's exact definition line. `def` names a function; parentheses hold its inputs, and `()` means no inputs. A **type hint** describes an expected type: `:` introduces an input type and `->` introduces the returned type; a final `:` starts an indented block. Indent the function body by four spaces; indent a block inside it by four more. `str` means text, `int` a whole number, and `bool` either `True` or `False`.

Quotes mark text; `""` is empty text. `=` assigns a value to a name; `==` compares two values. A **list** holds ordered items in `[]`; an **index** is an item's position, starting at zero, so `items[0]` selects the first item. A **tuple** groups values in order, such as `(2, 3)`; commas separate the values. `tuple[int, int, int]` describes three integers. A **dictionary** pairs keys with values in `{}`; `{"unit": "V"}` pairs the key `"unit"` with the value `"V"`. In `dict[str, str]`, both keys and values are text. `len(items)` counts items; `in` checks membership, and `not in` checks absence. `not` flips `True` to `False` and `False` to `True`. A `#` starts a comment that Python ignores. `+` adds; `-` subtracts, and before a number it marks a negative value.

For the paper traces and E3, represent heading with an index from 0 to 3, as shown below. Turning right moves to the next index, wrapping from 3 to 0; turning left moves to the previous index, wrapping from 0 to 3. Keep this movement reference handy. The direction list is `[(0, 1), (1, 0), (0, -1), (-1, 0)]`. Each pair says how F changes x and y:

| Heading index | Direction | Change in x | Change in y |
| --- | --- | --- | --- |
| 0 | north | 0 | 1 |
| 1 | east | 1 | 0 |
| 2 | south | 0 | -1 |
| 3 | west | -1 | 0 |

For F, `dx, dy = directions[heading]` unpacks the selected pair into two names. Add dx to x and dy to y. A **displacement** is the change from the starting position to the final position.

### Trace two cases by hand (part of the same 5 minutes)

On paper, trace `RFLF` and `FLF` once each. Start each case at position `(0, 0)` with heading 0 (north). After every command, record position `(x, y)` and heading index in separate columns. A turn changes only heading. For F, use the movement pair for that heading from the table above and add its two numbers to x and y.

<details>
<summary>Check your final positions and headings</summary>

- `RFLF`: final position `(1, 1)`; final heading 0 (north).
- `FLF`: final position `(-1, 1)`; final heading 3 (west).

</details>

## Exercises

### E1 — Ask before moving (QUIZ, ~5 min)

**Goal:** Choose useful clarifying questions before writing station code. Each question below asks which question and reason would help settle the vague interview task.

**New idea:** A **clarifying question** asks for a missing rule that could change your solution. Ask about accepted input, the required result, empty input and input size before coding. A quiz function returns chosen letters in a dictionary; this unrelated quiz chooses a unit for a time reading:

```python
def timer_answers() -> dict[str, str]:
    # Sample question T1: which unit measures time? A volts; B seconds.
    return {"T1": "B"}
print(timer_answers())  # {'T1': 'B'}
```

**Signature:** `def question_answers() -> dict[str, str]:`

**Examples:** `len(question_answers())` → `4`; `"Q1" in question_answers()` → `True`. These show the answer format, not the correct letters.

**Contract:** Return exactly the keys `"Q1"`, `"Q2"`, `"Q3"`, `"Q4"`, each with one uppercase option letter. Choose one option per question; do not return the option text.

Q1. Which question settles what to do with a character such as X?

- A. "What color is the probe?" Color decides which characters Python accepts.
- B. "Should other characters be rejected or ignored?" This changes the input check.
- C. No question is needed; every unrecognized character must mean forward.

Q2. Which question settles what counts as returning?

- A. "Must position alone match, or must heading also match?" This changes what state we compare.
- B. "Which editor do you use?" The editor decides whether heading matters.
- C. No question is needed; returning always requires the original heading.

Q3. Which question settles the no-command case?

- A. "What is the probe's serial number?" It tells us whether an empty string is legal.
- B. No question is needed; all strings contain at least one character.
- C. "May the string be empty, and what result should it give?" Otherwise this case has no agreed answer.

Q4. Which question helps choose how much work the solution can do?

- A. "What font is the operator using?" The font determines the number of loop steps.
- B. "How long can the string be?" A solution must handle the allowed input size.
- C. No question is needed; input length never affects running time.

**If you're stuck:**

1. Look for a missing rule about the input, result or amount of work.
2. Use `return {"Q1": "...", "Q2": "...", "Q3": "...", "Q4": "..."}` with your chosen letters replacing the dots.

### E2 — Check the command alphabet (~8 min)

**Goal:** Check whether the station can understand every character in a command string. This check accepts the alphabet; it does not decide whether the route is valid.

**New idea:** To check every item, look for one that breaks the rule. Return `False` when you find one; return `True` only after the loop finishes. In this different example, `>` means greater than, and a batch is safe only when every temperature is at most 60:

```python
def temperatures_safe(readings: list[int]) -> bool:
    for reading in readings:
        if reading > 60:
            return False
    return True
print(temperatures_safe([40, 65, 30]))  # False
print(temperatures_safe([]))  # True: nothing broke the rule
```

**Signature:** `def commands_ok(command: str) -> bool:`

**Examples:** `commands_ok("LRF")` → `True`; `commands_ok("FLX")` → `False`; `commands_ok("")` → `True`.

**Contract:** Return `True` only if every character is L, R or F; the empty string returns `True`. Return `False` for any other character, including lowercase letters. Do not print the result.

**If you're stuck:**

1. One good character does not prove that all the later characters are good.
2. Use `for letter in command:` and check `letter not in "LRF"`; keep your success return outside the loop.

### E3 — Run one pass (~10 min)

**Goal:** Simulate one pass of a probe program. Return its final x, y and heading index so the operator can inspect where it ended.

**New idea:** A direction can be an index in a circular list instead of four separate turning rules. The **remainder operator** `%` gives the remainder after division; with `% 4`, indices wrap from 3 to 0 and from -1 to 3. `+` adds and `-` subtracts, so adding one selects the next item and subtracting one selects the previous item. This different example rotates between three inspection trays:

```python
trays = ["load", "inspect", "unload"]
tray = 0
tray = (tray - 1) % 3
print(trays[tray])  # unload
tray = (tray + 1) % 3
print(trays[tray])  # load
```

**Signature:** `def run_once(command: str) -> tuple[int, int, int]:`

**Examples:** `run_once("F")` → `(0, 1, 0)`; `run_once("RFF")` → `(2, 0, 1)`; `run_once("")` → `(0, 0, 0)`.

**Contract:** Each call starts at x = 0, y = 0, heading = 0 and runs the string once, returning `(x, y, heading)`. Inputs here contain only L, R and F; no rejection code is needed. Use heading indices 0 = north, 1 = east, 2 = south, 3 = west, in the movement reference above.

**If you're stuck:**

1. Track three numbers; a turn changes heading, while a forward move changes position.
2. Use `if`, `elif` (another condition) and `else` (the remaining case) inside the command loop; L subtracts one from heading and R adds one, both with `% 4`. Look up `directions[heading]` for F; turns do not move the head.

### E4 — Decide whether repetition drifts (~12 min)

**Goal:** Tell the operator whether repeating a probe program stays bounded, using at most four complete passes. Reuse your alphabet check and one-pass simulator.

**New idea:**

<details>
<summary>Try for five minutes first, then open</summary>

After one pass the heading has turned by 0, 90, 180 or 270 degrees. With zero turn, a nonzero displacement repeats in the same direction forever, while zero displacement already returns to the start. With 180 degrees, two displacements cancel; with 90 or 270 degrees, four rotated displacements cancel, so checking the position after four whole passes covers every case. For a different worked example, a display animation moves a label by `(2, 1)` and rotates that jump clockwise each frame; its four jumps cancel:

```python
jumps = [(2, 1), (1, -2), (-2, -1), (-1, 2)]
x = 0
y = 0
for dx, dy in jumps:
    x = x + dx
    y = y + dy
print((x, y))  # (0, 0)
```

</details>

**Signature:** `def is_valid(command: str) -> bool:`

**Examples:** `is_valid("F")` → `False`; `is_valid("RF")` → `True`; `is_valid("FX")` → raises `ValueError`.

**Contract:** Return `True` if the repeated route stays bounded, which is equivalent to being at `(0, 0)` after four whole passes; otherwise return `False`. Empty input is valid, and heading is not part of the position comparison. Raise `ValueError` if any character is outside L, R and F, even after a prefix that returns to the start.

**If you're stuck:**

1. Four passes mean one continuous journey; four separate `run_once(command)` calls would each reset to the start.

<details>
<summary>Hint 2</summary>

Check `commands_ok` first; reject with `raise ValueError("Use only L, R and F")`. Then use string repetition: `command * 4` makes four consecutive copies, which `run_once` can simulate together.

</details>

### E5 — Explain your decision (QUIZ, ~5 min)

**Goal:** Explain the interview examples to the station team and estimate the work your simulation does. Also spot a result that is displayed but never returned.

**New idea:** **Linear work**, written **O(n)**, grows in proportion to the input length n, even when you scan it a fixed number of times. Four scans take 4n item visits; doubling n doubles that work. Making a fixed number of copies also uses O(n) extra storage, since their size grows with n. This different example counts visits in three scans of a reading list; `range(3)` supplies 0, 1 and 2 for three scans:

```python
readings = [10, 20, 30, 40]
visits = 0
for scan in range(3):
    for reading in readings:
        visits = visits + 1
print(visits)  # 12: three times the four readings
```

**Signature:** `def reasoning_answers() -> dict[str, str]:`

**Examples:** `len(reasoning_answers())` → `5`; `"Q5" in reasoning_answers()` → `True`.

**Contract:** Return exactly `"Q1"` through `"Q5"`, each mapped to one uppercase option letter. Choose the option that gives both the correct result and the correct reason.

Q1. What about `"F"` and `"LRF"`?

- A. Both valid: any forward move eventually comes back on an infinite grid.
- B. Only LRF is valid: a left and right turn cancel the forward move.
- C. Both invalid: each pass ends one step north and still faces north, so repetition drifts.

Q2. What about `"L"` and `"FLLF"`?

- A. Only L is valid: FLLF returns facing south, which is forbidden.
- B. Both valid: L never changes position, and FLLF returns to the start; heading need not match.
- C. Both invalid: turning always changes position.

Q3. What about `"LF"`?

- A. Valid: successive passes move west, south, east, north, returning after four passes.
- B. Invalid: the first pass ends away from the start, so later passes cannot help.
- C. Valid: a left turn does not change heading, so the second pass undoes the first.

Q4. For a string of length n, what does checking it and simulating `command * 4` cost? Here `*` repeats the string, rather than doing numeric multiplication.

- A. O(1) work and storage: four passes always take the same time and space.
- B. O(n squared) work: an outer loop always makes work grow like n times n.
- C. O(n) work: at most n validation checks plus 4n command steps; the repeated string uses O(n) extra storage.

Q5. An operator writes this function. Why does the test expecting `True` instead get `None`?

```python
def ready() -> bool:
    print(True)
```

- A. The test should compare a list to a number instead.
- B. `print` displays True but does not return it; the function needs a `return` statement.
- C. Replace an assignment `=` with `==` inside the function name.

**If you're stuck:**

1. Trace position separately from heading; returning after a later pass still counts.
2. Use a dictionary with keys Q1 through Q5; revisit E3's direction table, E4's four-pass reasoning, and How this works for `return` versus `print`.
