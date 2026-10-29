# d00-hello — Your first station check

**Time:** about 5 minutes · **Read first:** the repo README, Set up once · **You edit:** `starter/hello.py` (already correct; no edit needed)

## What you're building

A test station greets the operator with its name. This tiny check proves Python and the test runner work before you start writing instrument code.

## How this works

1. Open `starter/hello.py` and read the supplied function. This setup check is already implemented. Later sets ask you to replace `raise NotImplementedError(...)` lines; don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d00-hello** (or run `bash tools/run.sh d00-hello` / `tools\run.ps1 d00-hello`). Expect `Exercises: 1 / 1 passed` immediately.
3. Report **all pass / partial / stuck** in the tracker. If setup fails, report stuck with the first error you see.

A **function** is a named piece of code you can call. A **string** is text; `str` in the signature says the input and output are strings. An **f-string** inserts a value into text:

```python
channel = "CH2"
message = f"Reading {channel}"
print(message)  # Reading CH2
```

## Exercises

### E1 — Station greeting (easy, ~5 min)

**Goal:** Check that the station greeting matches the supplied name exactly.

**Signature:** `def station_greeting(name: str) -> str`

**Example:** `station_greeting("A1")` → `"Hello from test station A1"`

**Watch out:** Keep the spaces and capitalization exactly as shown. An empty name returns `"Hello from test station "`, including the final space. The test tries several names, but they all belong to one exercise.

**Reread:** the repo README, Reading results.
