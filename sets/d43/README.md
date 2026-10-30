# d43 — An operator status page with FastAPI

**Time:** about 45 minutes · **Read first:** FastAPI tutorial: [First Steps](https://fastapi.tiangolo.com/tutorial/first-steps/), [Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/), and [Testing](https://fastapi.tiangolo.com/tutorial/testing/); [The Linux Command Line, chapter 14: Package Management](https://linuxcommand.org/tlcl.php) · **You edit:** `starter/statuspage.py`

## What you're building

An operator needs to see whether a chassis test station is running and which completed test runs failed. Build the service that supplies this information to an operator status page. A **test run** is one execution of a station's test sequence; its result is `PASS` or `FAIL`.

## How this works

1. Replace the `raise NotImplementedError(...)` lines in `starter/statuspage.py`. The imports, models, application, starting data, and route decorators are supplied. Don't edit `tests/`.
2. Press **Ctrl+Shift+B → Test: d43** (or run `bash tools/run.sh d43` / `tools\run.ps1 d43`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

An **API** (application programming interface) lets another program request information or changes. **FastAPI** is the Python framework used here to handle those requests; `app` is the supplied application object.

- **HTTP** is the request/response protocol used by web clients. A **route** pairs a method with a URL path: `GET` reads information and `POST` submits information. A **decorator**, such as `@app.get(...)`, connects a function to a route.
- **JSON** is a text format for objects and lists. FastAPI converts returned dictionaries and models to JSON; Python `True` becomes JSON `true`.
- A **Pydantic model** is a class that declares data fields and validates their types. `BaseModel` supplies that behavior; `Literal[...]` restricts a field to the listed values. An attribute is a named value on an object, accessed with a dot, such as `run.state`. Both models below are already declared for you.
- JSON `null` represents a missing value and becomes Python `None`. A **request body** carries submitted JSON. A **path parameter** is part of the URL, such as `run-17` in `/runs/run-17`. A **query parameter** follows `?`, such as `state=FAIL` in `/runs?state=FAIL`.
- An HTTP **status code** reports the outcome: `200` means success, `404` means not found, and `422` means the submitted data failed validation. `HTTPException` asks FastAPI to send a chosen error code and message.
- **In-memory storage** keeps data in Python variables for this process only; it is lost on restart. `current_status` holds one `Status`; `runs` is a dictionary mapping run IDs (identifying strings) to `Run` objects. `global current_status` inside a function lets an assignment replace the module's variable.
- A **timestamp** is a numeric time value. Here `started_at` is an integer number of seconds since 1970-01-01 00:00:00 UTC, the common time standard. Larger values mean later starts.
- **Package management** means installing, updating, and removing software through a system's package tools. A **dependency** is another package your code needs; the runner already provides this set's Python dependencies. FastAPI's `TestClient` sends requests inside the test process, so you do not need to start a server or open a network port.

For example, this reads model attributes and sorts a list by one attribute. A `lambda` is a short unnamed function. The `key` function chooses the value to compare, and `reverse=True` puts larger values first:

```python
class Reading(BaseModel):
    channel: str
    volts: float
readings = [Reading(channel="CH1", volts=3.2), Reading(channel="CH2", volts=4.1)]
highest_first = sorted(readings, key=lambda reading: reading.volts, reverse=True)
```

## Exercises

### E1 — Service health (easy, ~6 min)

**Goal:** Let the operator's page check that the service responds.

**Signature:** `def health() -> dict[str, bool]` on `GET /health`.

**Contract:** Return HTTP `200` and exactly `{"ok": true}` as JSON. Repeated reads return the same response and change no stored data.

**Example:** `GET /health` → `200`, `{"ok": true}`.

**Watch out:** Return a Python dictionary, with the boolean `True`. The supplied `app` and decorator handle the HTTP response.

**Reread:** FastAPI, First Steps: create an app and a path operation; The Linux Command Line, chapter 14: Package Management, for the distinction between system packages and the Python dependencies supplied here.

### E2 — Station operating status (easy, ~14 min)

**Goal:** Let station software publish its status and let the operator read it.

**Signatures:** `def get_status() -> Status` on `GET /status`; `def set_status(status: Status) -> Status` on `POST /status`.

**Contract:** `Status` has `station: str` and `state: Literal["IDLE", "RUNNING", "FAULT"]`. `IDLE` means waiting, `RUNNING` means testing, and `FAULT` means the station needs attention. Initially, `current_status` is `Status(station="CHASSIS-01", state="IDLE")`. GET returns that current model with HTTP `200`. POST replaces it with the submitted, validated model and returns the new model with HTTP `200`. Later GET requests must see the update. Responses contain `station` and `state`.

Both body fields are required. A non-string station, a missing field, or any other state (including lowercase or null) must return `422` and leave the previous status intact. An empty station string is allowed; no additional station-name validation is required. FastAPI and the supplied `Status` model perform the validation before calling your handler. Error-detail wording for `422` is not part of the contract.

**Example:** POST `/status` with `{"station": "B2", "state": "RUNNING"}` → `200` and that same object; the next GET `/status` returns it too.

**Watch out:** Replace the module's `current_status`, not a new local variable. Each test starts with the initial status; real requests share the current value until process restart.

**Reread:** FastAPI, First Steps: path operation functions; Testing: `TestClient`, especially sending JSON in a request.

### E3 — Find one completed run (easy, ~10 min)

**Goal:** Let an operator open a completed chassis test run by its ID.

**Signature:** `def get_run(run_id: str) -> Run` on `GET /runs/{run_id}`.

**Contract:** The supplied `Run` model has `run_id: str`, `station: str`, `state: Literal["PASS", "FAIL"]`, and `started_at: int`. The module's `runs: dict[str, Run]` starts empty; the tests insert records directly, with each dictionary key equal to its record's `run_id`. Look up the exact, case-sensitive ID. Return the full model with HTTP `200` if present. If absent, raise `HTTPException(status_code=404, detail="Run not found")`, producing JSON `{"detail": "Run not found"}`. Reads never remove or modify records.

**Example:** If `runs["run-17"]` holds `Run(run_id="run-17", station="B2", state="FAIL", started_at=100)`, GET `/runs/run-17` → `200`, `{"run_id": "run-17", "station": "B2", "state": "FAIL", "started_at": 100}`.

**Watch out:** A missing ID is an HTTP `404`, not a dictionary lookup exception. No route to create runs is needed.

**Reread:** FastAPI, Path Parameters: declaring and reading path parameters; Testing: checking response codes and JSON.

### E4 — Latest run results (medium, ~15 min)

**Goal:** Put the newest failures at the top of the operator's run list.

**Signature:** `def list_runs(state: str | None = None) -> list[Run]` on `GET /runs`.

**Contract:** Return HTTP `200` with a JSON list of full run records. If `state` is omitted (`None`), include every stored run. If supplied, include only records whose `state` equals that string exactly. An unknown, lowercase, or empty query value matches nothing and returns `[]`. Sort included records by `started_at`, largest first. If timestamps tie, preserve their dictionary insertion order; Python's `sorted` already preserves the input order for equal keys. An empty store returns `[]`. Do not change the store or its records.

**Example:** Given a `FAIL` run at time 100, a `PASS` run at 300, and a `FAIL` run at 200, GET `/runs?state=FAIL` returns the full records at 200 then 100. GET `/runs` returns all three at 300, 200, 100.

**Watch out:** `/runs` and `/runs/{run_id}` are separate routes. Filter the dictionary's values (the `Run` objects), and sort by numeric time, not by ID.

**Reread:** FastAPI, First Steps: route functions; Testing: GET requests with query strings and JSON assertions. An optional function argument becomes the query parameter here.
