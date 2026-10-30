# d41 — systemd services and config files

**Time:** about 45 minutes · **Read first:** [systemd.service: what a unit file says](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html), [systemd.unit](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html), [journalctl](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html), [tomllib](https://docs.python.org/3/library/tomllib.html) and [configparser](https://docs.python.org/3/library/configparser.html) · **You edit:** `starter/chassis-demo.service` and `starter/units.py`

## What you're building

A chassis test station needs a predictable way to start its Python process and load its instrument settings. You will describe that process in a service file, preserve repeated settings while reading files, and give the operator useful configuration errors. These checks read local files on Windows or Linux; they never install or start a service.

## How this works

1. For E1, replace the entire placeholder in `starter/chassis-demo.service`. For E2–E4, replace the `raise NotImplementedError(...)` lines in `starter/units.py`. Don't edit `tests/`.
2. Press Ctrl+Shift+B → **Test: d41** (or run `bash tools/run.sh d41` / `tools\run.ps1 d41`). At first you'll see `Exercises: 0 / 4 passed`. Rerun after each exercise. The E1 placeholder marker makes its file-only exercise report `NotImplementedError` until you replace it.
3. Report all pass / partial / stuck in the tracker.

**systemd** is a Linux manager that starts and supervises processes. A **service** is a process it manages. A **unit file** describes something systemd manages; a `.service` file describes a service. A **section** is a group headed by `[Name]`; a **directive** is a `Key=value` setting within it. A **target** groups units into a startup milestone. The **root** user (numeric user ID `0`) has unrestricted system privileges; a station process should use a separate account.

**Parsing** turns file text into Python values. **Validation** checks those values against a contract. Python's `configparser` reads section/key files, but by default changes key names to lowercase and cannot preserve all repeated assignments. E1 uses `ConfigParser(strict=False)` with case preserved, interpolation disabled, and `=` as the delimiter (the character separating key and value); repeated keys then keep only their last value. E2 writes a small parser to keep every value. **Interpolation** means replacing special placeholders inside values; our parser treats values as literal text instead.

A **nested dictionary** is a dictionary containing other dictionaries. A `list[str]` is a list of strings; repeated directives become lists. `setdefault(key, default)` inserts the default only when the key is absent, then returns the stored value:

```python
commands = {}
commands.setdefault("Query", []).append("MEAS:VOLT?")
commands.setdefault("Query", []).append("SYST:ERR?")
# {"Query": ["MEAS:VOLT?", "SYST:ERR?"]}
```

**TOML** is a configuration text format with explicit strings, numbers, lists, and tables. A **table** is a group of named values, written `[station]`; `[[instruments]]` starts another table in a list of instruments. `tomllib.load` reads a file opened in binary mode (`"rb"`) and returns a dictionary. A **key path** locates a nested value: `instruments[1].resource` means the second instrument's resource. `dict[str, Any]` means string keys whose values may have different types; `Any` comes from `typing`.

## Exercises

### E1 — Describe the station service (easy, ~8 min)

**Goal:** Replace `starter/chassis-demo.service` with a unit that follows the deployment checklist below. This is a text-file exercise with no Python function to write.

| Section | Directive | Required value |
| --- | --- | --- |
| `Unit` | `Description` | Any nonempty description of the station |
| `Unit` | `After` | Whitespace-separated target names including `network-online.target` |
| `Unit` | `Wants` | Whitespace-separated target names including `network-online.target` |
| `Service` | `Type` | `simple` |
| `Service` | `ExecStart` | Absolute Linux path to `python` or `python3`, then `-m chassis`, then optional arguments |
| `Service` | `Restart` | `on-failure` |
| `Service` | `RestartSec` | A positive integer number of seconds, such as `3` |
| `Service` | `User` | Any nonempty account name other than `root` or `0` |
| `Install` | `WantedBy` | Whitespace-separated target names including `multi-user.target` |

**Example:** `Description=Rack 7 measurement worker` gives the service an operator-readable label. Choose the remaining lines from the checklist.

`After` orders this service after the named unit; `Wants` asks systemd to start that unit too. `network-online.target` marks network readiness according to the station's network setup. `Type=simple` means systemd starts the process directly. `ExecStart` gives the command, and `-m chassis` runs the Python module named `chassis`. `Restart=on-failure` retries after a process failure; `RestartSec` delays that retry. `WantedBy=multi-user.target` connects an enabled service to the usual non-graphical operating state. **Enabling** a service means arranging for its startup at boot.

**Watch out:** Use exact section/key capitalization. Write each required directive once. Use an unquoted absolute Linux path with no spaces, such as `/opt/station/bin/python3`; it need not exist on this computer. Extra arguments are split on whitespace; quoted commands and shell wrappers are outside this exercise. Extra settings are allowed. The tests inspect the file structurally, without requiring the account or chassis package to exist. On a real station, `journalctl -u chassis-demo.service` displays the service's **journal**, its collected log messages; you do not need to run this command here.

**Reread:** systemd.service, `Type=`, `ExecStart=`, `Restart=`, `RestartSec=`; systemd.unit, `Description=`, `Wants=`, `After=`, and `[Install]`; journalctl, `-u` / `--unit=`. `User=` is an execution setting linked from systemd.service.

### E2 — Preserve repeated directives (medium, ~12 min)

**Goal:** Read a UTF-8 unit file (UTF-8 is the text-to-bytes encoding) into section names, then keys, then lists of values.

**Signature:** `def parse_unit(path: str | Path) -> dict[str, dict[str, list[str]]]`

**Example:** File text `[Service]\nEnvironment=MODE=demo\nEnvironment=RACK=7\n` → `{"Service": {"Environment": ["MODE=demo", "RACK=7"]}}`. Here `\n` represents a newline.

Contract:

- Accept a string path or `pathlib.Path`. Strip surrounding whitespace on every line. Skip blank lines and whole-line comments starting with `#` or `;` after stripping.
- A stripped line beginning with `[` and ending with `]` is a section heading. Strip the name inside the brackets; it must not be empty. Preserve capitalization. Repeated section headings reuse the same dictionary. Keep empty sections.
- Every other non-comment line must have a current section and contain `=`. Split at the first `=` only; strip surrounding whitespace from key and value. The key must not be empty. Append the value to that key's list, preserving assignment order. An empty value is still an entry: `[""]`.
- Keep all characters inside values, including additional `=`, `%`, `#`, and `;`. There are no inline comments, placeholder substitutions, or special reset behavior for empty values.
- A comment-only or empty file returns `{}`. An invalid line raises `ValueError` whose message contains `line N`, with the physical line number starting at 1 (including comments and blanks). A missing file propagates `FileNotFoundError`.

**Watch out:** This is a single-line subset of unit syntax. It does not join continued lines or interpret commands and systemd placeholders. `configparser(strict=False)` loses earlier repeated values, so use line iteration and dictionaries for E2. No dependency on E1 is needed.

**Reread:** configparser, "Supported INI File Structure", "Customizing Parser Behaviour" (`strict`, `optionxform`, `interpolation`); systemd.unit, the unit-file syntax introduction. **INI** means the section/key text format described by configparser.

### E3 — Give the operator a deployment checklist (medium, ~12 min)

**Goal:** Check the parsed dictionary without starting the service or changing the dictionary. Return every problem in the order below, at most one problem per row. Tests supply dictionaries directly, so E3 does not depend on E2.

**Signature:** `def validate_unit(parsed: dict[str, dict[str, list[str]]]) -> list[str]`

**Example:** An otherwise valid unit with `User=["root"]` and no `Restart` → `["Restart missing", "User is root"]`.

Input has E2's dictionary/list/string shape. Missing sections and keys are allowed. For `After`, `Wants`, and `WantedBy`, combine tokens (words separated by whitespace) from **all** values and check for an exact target token. For every other required key use only its final value, stripped; an absent key, empty list, or blank final value counts as missing. Ignore extra sections and keys.

| Check, in this order | Problem string |
| --- | --- |
| Final `Unit.Description` is missing | `Description missing` |
| `Unit.After` lacks the network target | `After must include network-online.target` |
| `Unit.Wants` lacks the network target | `Wants must include network-online.target` |
| Final `Service.Type` is not `simple`, including missing | `Type must be simple` |
| Final `Service.ExecStart` fails E1's command rule, including missing | `ExecStart must run an absolute python -m chassis command` |
| Final `Service.Restart` is missing | `Restart missing` |
| Otherwise, `Service.Restart` is not `on-failure` | `Restart must be on-failure` |
| Final `Service.RestartSec` is missing | `RestartSec missing` |
| Otherwise, `int(value)` fails or is at most zero | `RestartSec must be positive whole seconds` |
| Final `Service.User` is missing | `User missing` |
| Otherwise, `Service.User` is `root` or `0` | `User is root` |
| `Install.WantedBy` lacks the boot target | `WantedBy must include multi-user.target` |

**Watch out:** Return `[]` when all checks pass. Whole seconds here use Python's `int` conversion: reject `0.5` and `3s`. This checklist deliberately covers fewer choices than systemd supports. It does not interpret empty assignments as dependency resets, verify accounts, or check paths on disk. Do not mutate (change) the input dictionary or its lists.

**Reread:** systemd.service, `Type=`, `ExecStart=`, `Restart=`, and `RestartSec=`; systemd.unit, `Wants=`, `After=`, `[Install]`.

### E4 — Load instrument settings with useful errors (medium, ~13 min)

**Goal:** Load TOML with `tomllib` and check a small station schema. A **schema** describes required keys and the types of their values. This exercise uses the station/instrument portion of the deployment configuration.

**Signature:** `def load_station_toml(path: str | Path) -> dict[str, Any]`

**Example file:**

```toml
[station]
name = "Rack 7"

[[instruments]]
id = "psu1"
kind = "psu"
resource = "TCPIP::10.0.0.5::5025::SOCKET"
```

This returns `{"station": {"name": "Rack 7"}, "instruments": [{"id": "psu1", "kind": "psu", "resource": "TCPIP::10.0.0.5::5025::SOCKET"}]}`. A **resource** is the instrument address string; this loader stores it without connecting. `psu` identifies a power supply; `dmm` commonly identifies a digital multimeter.

Validate in this order, stopping at the first problem:

1. `station` must exist and be a dictionary (a TOML table). On failure raise `ValueError` containing `station`.
2. `station.name` must exist and be a string. On failure name `station.name`.
3. `instruments` must exist and be a list. On failure name `instruments`.
4. Visit instruments in list order, with indexes starting at 0. Each item must be a dictionary; otherwise name `instruments[i]`. In each item check `id`, then `kind`, then `resource`: each must exist and be a string. Name the full path on failure, for example `instruments[1].resource`.

Return the complete parsed dictionary, preserving unknown keys, values, and instrument order. Empty strings and an empty instrument list are valid. Only key presence and Python types are checked: no uniqueness, allowed-kind, address, or cross-reference checks. Accept strings and `Path` objects as paths. Open in binary mode for `tomllib.load`. Propagate `tomllib.TOMLDecodeError` for invalid TOML text and `FileNotFoundError` for a missing file; only schema errors need a key path. `TOMLDecodeError` is itself a subclass of `ValueError`.

**Watch out:** Missing keys must produce your useful `ValueError`, rather than an accidental `KeyError`. If several settings are wrong, follow the validation order above. A TOML boolean like `true` is not a string.

**Reread:** tomllib, `load`, the example, and the conversion table (TOML table → `dict`, array → `list`, string → `str`).
