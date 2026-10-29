# d34 — Git branches, code review and CI

**Time:** about 45 minutes · **Read first:** GitHub Actions: [Building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python); *The Pragmatic Programmer*, topic “Test to Code” (your book); *Pro Git*, “Basic Branching and Merging” and “Contributing to a Project” · **You edit:** `starter/review_fix.py` and `starter/ci.yml`

## What you're building

A chassis test station compares measured bus voltages (voltages on shared electrical supply lines) with allowed limits. You will address two review comments, describe automated checks for the change, and validate the team's branch names. A **code review** is another developer checking a proposed change before it becomes shared station software.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/review_fix.py`. E1 and E2 include the proposed buggy bodies in their docstrings (text attached to a function); copy each body out and fix it. For E3, replace the entire placeholder in `starter/ci.yml`. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d34** (or run `bash tools/run.sh d34` / `tools\run.ps1 d34`). At first you'll see `Exercises: 0 / 4 passed`, all reported as `NotImplementedError`; this includes the untouched YAML placeholder. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

**Git** tracks versions of files. A **branch** is a named line of Git development. A **commit** records a snapshot of changes. A **pull request (PR)** asks reviewers to merge a branch into the shared branch. **Continuous integration (CI)** runs automated checks when code is pushed or a PR changes. A **regression** is previously working behavior broken by a change.

A GitHub Actions **workflow** is a YAML file describing automated work. **YAML** is a text format where indentation groups settings: a **mapping** holds `key: value` entries, and a **list** uses `-` entries. A **job** runs on a **runner**, the computer GitHub provides; its **steps** run in order. A step's `uses` selects a reusable action, while `run` gives a shell command. For example, this unrelated workflow fragment gives an operator label to later steps:

```yaml
name: Operator label
jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - run: echo bench-a
```

`pytest` runs behavioral tests; `mypy` checks Python type hints without operating hardware. `pip` installs Python packages. `python -m <tool>` runs an installed Python tool. An **inclusive** limit accepts its endpoints. A **finite** number is neither infinity nor NaN (**not a number**, an invalid numeric reading).

## Exercises

### E1 — Review the voltage boundary (easy, ~8 min)

**Goal:** Fix the boundary comparison in `within_limits`.

**Signature:** `def within_limits(value: float, low: float, high: float) -> bool`

**Review comment:** “The approved station limits include both endpoints. Your strict comparisons reject a bus reading exactly on the low or high limit. Keep those readings passing, and reject readings outside the limits.” The supplied buggy body is `return low < value < high`.

Return `True` exactly when `value` is finite and `low <= value <= high`; otherwise return `False`. The caller guarantees finite bounds with `low <= high`; you do not need to validate the bounds. Equal bounds are allowed. Values and bounds use the same unit, volts.

**Example:** `within_limits(22.0, 22.0, 26.0)` → `True`; `within_limits(26.1, 22.0, 26.0)` → `False`.

**Watch out:** NaN and positive or negative infinity must return `False`. Negative voltages are allowed when the supplied bounds allow them.

**Reread:** *The Pragmatic Programmer*, “Test to Code”: connect the endpoint requirement to a test before changing the comparison.

### E2 — Review all station channels (easy, ~9 min)

**Goal:** Fix the premature return in `failed_channels`. A **channel** here is one named voltage measurement.

**Signature:** `def failed_channels(readings: dict[str, float], low: float, high: float) -> list[str]`

**Review comment:** “The return inside the loop stops after the first channel. An operator needs every failing channel, even when the first channel passes. Finish the loop before returning.” The full buggy body is supplied in the function's docstring.

`readings` maps unique channel names to voltage values. Apply E1's rule to every value, using the same bounds for all channels. Return a new list containing exactly the failing channel names, in Python's normal string sort order. Return `[]` for empty or all-passing input. Do not change the input dictionary, its values, or its insertion order (the order its entries were added). Bounds have E1's guarantees. You may call `within_limits`.

**Example:** `failed_channels({"bus_b": 28.0, "bus_a": 24.0}, 22.0, 26.0)` → `["bus_b"]`.

**Watch out:** Include non-finite readings as failures. Complete E1 first if you reuse it. Each call returns its own list.

**Reread:** *The Pragmatic Programmer*, “Test to Code”: test the case that exposes the defect, including a passing first channel and failing later channel.

### E3 — Describe the station's CI checks (medium, ~16 min)

**Goal:** Replace `starter/ci.yml` with a GitHub Actions workflow that catches future station regressions.

**File contract:** Use a YAML mapping with these settings:

- `on` includes both `push` and `pull_request`, without event filters. Use a list of those names, or a mapping with empty values. Quoting the key as `"on"` avoids older YAML parsers treating it as a boolean.
- `jobs` contains a job named `checks`, with `runs-on: ubuntu-latest` (GitHub's hosted Linux runner).
- Its `steps` use `actions/checkout@<version>` to download the repository, then `actions/setup-python@<version>` with `python-version: '3.12'` under `with`. An action version identifies a release, such as `@v4`; any nonempty version is accepted. Quote `'3.12'` so YAML reads text rather than a decimal number.
- After setup, use separate `run` steps in this order: `python -m pip install -r requirements.txt`, `python -m pytest sets/d34`, then `python -m mypy --strict sets/d34/starter`. Bare `pip`, `pytest`, and `mypy` commands are also accepted. Here `-r` reads the package list, and `--strict` enables mypy's strict checks. Each required run step contains just its listed command, with no additional arguments or commands. Use these exact paths; commands run from the exercise repository root. Do not set working-directory overrides on jobs or steps, or in workflow/job defaults.
- Run the job and its steps unconditionally: no `if` conditions or enabled `continue-on-error` settings. A failed check must fail the workflow. Use direct commands, without shell wrappers, pipes, or ignored errors.

**Example:** A Python setup step has a `uses` entry and a sibling `with` mapping; `python-version` belongs inside that mapping. The GitHub reading shows this structure.

**Watch out:** This exercise only parses and inspects the file using **PyYAML**, the installed YAML reader. It never runs the workflow, downloads actions, or installs packages. `starter/ci.yml` is a practice location; GitHub discovers real workflows under `.github/workflows/`. Keep the exercise file in `starter/` for these tests.

**Reread:** GitHub Actions, “Building and testing Python”: “Specifying a Python version”, “Installing dependencies”, and “Testing your code”.

### E4 — Validate a station-work branch (easy, ~7 min)

**Goal:** Implement the team's branch naming convention for reviewed station changes.

**Signature:** `def branch_name_ok(name: str) -> bool`

Return `True` only for the complete form `feature/<ticket>-<slug>` or `fix/<ticket>-<slug>`. A **ticket** is a work-item identifier: exactly uppercase `CTS-` followed by one or more ASCII digits `0`–`9`; leading zeros are allowed. A **slug** is a short description made of one or more lowercase ASCII letters or digits, optionally separated into groups by single hyphens. No leading, trailing, or consecutive hyphens in the slug. **ASCII** here means the English letters `a`–`z` and digits `0`–`9`, rather than other alphabets or digit forms.

**Example:** `branch_name_ok("feature/CTS-34-bus-limits")` → `True`; `branch_name_ok("fix/CTS-34-Bus")` → `False`.

**Watch out:** Match the whole string, including its end. Do not trim spaces or newlines. Reject empty text, extra slashes, underscores, and any other prefix. `re.fullmatch` from Python's `re` module can match a **regular expression**, a pattern describing allowed text; ordinary string checks are also fine.

**Reread:** *The Pragmatic Programmer*, “Test to Code”, for testing both accepted and rejected names; *Pro Git*, “Basic Branching and Merging” for branch creation and “Contributing to a Project” for a focused contribution and review.

## Hands-on git checklist (~5 min; not scored)

Do this in your own capstone repository (the longer chassis-tester project), where you can push a branch. These actions are practice for you; the exercise runner does not run Git or check a PR.

- Start from your shared branch with a clean working tree (no uncommitted changes). Create your work branch with `git switch -c fix/CTS-34-limit-review`.
- Make a small limit-checker change and a regression test in that project. Run its tests locally. Use `git diff` to inspect the changed lines before recording them.
- Stage only those files with `git add <file-paths>`, then commit with `git commit -m "Fix inclusive voltage limit review"`.
- Publish the branch with `git push -u origin fix/CTS-34-limit-review`. `origin` is the usual name for your GitHub repository connection; `-u` remembers that branch's destination.
- Open a PR in your own repository. Describe the defect, resulting behavior, and test command/result. Read the PR's diff (the changed lines) as a reviewer and check its CI result. If the repository has no workflow yet, CI will not appear automatically; record that in the PR instead of claiming checks ran.
