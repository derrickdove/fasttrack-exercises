# d36 — Shell scripting for test stations

**Time:** about 45 minutes · **Read first:** [The Linux Command Line](https://linuxcommand.org/tlcl.php), ch. 24, 27, 32 (scripts, flow control, positional parameters); [Missing Semester: Security and Cryptography](https://missing.csail.mit.edu/2020/security/), SSH keys; also [Missing Semester: Shell Tools and Scripting](https://missing.csail.mit.edu/2020/shell-tools/), scripting · **You edit:** `starter/collect_logs.sh`, `starter/check_station.sh`

## What you're building

A test station is the computer that controls instruments and records chassis test results. Give its operator a log collector and a configuration checker to run before a shift. These exercises work on local files; SSH (a secure connection to another computer) and SSH keys (credentials used to authenticate that connection) are reading context only.

## How this works

1. Replace the unfinished `printf` / `exit 99` bodies in the two Bash files. Keep the first `#!/usr/bin/env bash` line, which identifies the interpreter (the program that runs the script). No Python edits are needed; don't edit `tests/` or the supplied `starter/scripts.py` helper.
2. Press **Ctrl+Shift+B → Test: d36** (or run `bash tools/run.sh d36` / `tools\run.ps1 d36`). Initially expect `Exercises: 0 / 4 passed` with `NotImplementedError`: the tests translate the shell placeholders into that Python exception. Rerun after each exercise.
3. Report **all pass / partial / stuck** in the tracker.

Install Bash, a command interpreter, or use the repo's Codespaces option. Git Bash counts on Windows. Tests skip with a clear message if `bash` is missing; skipped exercises are unfinished. Save `.sh` files with LF (Unix-style line endings).

A **positional parameter** such as `$1` is an argument passed to the script; `$#` is the argument count. An **exit status** is a number returned to the caller: zero means success. **stdout** is ordinary output; **stderr** is diagnostic output. A **glob**, such as `*.log`, matches filenames. Quote variable expansions so a path containing spaces remains one argument. A **pipeline** joins commands with `|`. A **key=value** line associates a setting name with text. A Bash **array** stores several values, for example missing setting names.

```bash
# A small example, independent of the exercises:
if [[ $# -ne 1 ]]; then
    printf '%s\n' 'Give one instrument name' >&2
    exit 2
fi
printf 'Selected: %s\n' "$1"
```

## Exercises

### E1 — Collect a station's logs (easy, ~12 min)

**Goal:** Copy station logs into a dated folder without losing files whose names contain spaces.

**Signature:** `bash starter/collect_logs.sh SRC DEST`

`SRC` must be an existing directory. Accept exactly two arguments. On a wrong argument count or invalid `SRC`, print `Usage: bash collect_logs.sh SRC DEST` followed by a newline to stderr, leave stdout empty, and exit 2 before creating output.

On success, obtain the current local date with `date +%Y%m%d`. Here `YYYYMMDD` means four-digit year, two-digit month, two-digit day. Create `DEST/YYYYMMDD/`, including missing parents, even if there are no logs. Copy every regular file (an ordinary file, not a directory) that is non-hidden (its name does not start with `.`) directly inside `SRC` whose name ends in lowercase `.log`. Do not search child directories. All modification times qualify: the date labels collection time, with no age cutoff. Leave source files intact, replace destination files of the same name, and leave unrelated destination files intact. Copy each selected file with `cp` (the file-copy command) so operating-system errors can be detected in E2. Print nothing on success and exit 0.

**Example:** On 2031-04-05, `collect_logs.sh "bench logs" archive` copies `bench logs/power check.log` into `archive/20310405/power check.log`.

**Watch out:** A directory named `old.log` is not a log file. An unmatched glob must not become a literal filename to copy. Source and destination are separate directory trees; symlinks are outside this exercise's inputs.

**Reread:** The Linux Command Line ch. 24, "Writing Your First Script," and ch. 32, "Positional Parameters"; Missing Semester "Shell Tools and Scripting," shell scripting and quoting.

### E2 — Stop after a collection failure (medium, ~8 min)

**Goal:** Prevent an incomplete archive from being reported as successful.

**Signature:** Extend `collect_logs.sh` with `set -euo pipefail`, before its work begins.

`-e` stops on a failed command, `-u` rejects an unset variable, and `pipefail` makes a pipeline fail if any component fails. Keep E1's usage behavior: check `$#` before reading `$1` or `$2`. A failure of `date`, `mkdir` (the directory-creation command), or `cp` must stop the script with a nonzero status. After the first failed copy, do not attempt another copy. No rollback is required: files already copied may remain. The tests supply a failing `cp` command; do not hide its failure in a conditional or overwrite its status.

**Example:** If copying the first log fails, the second log is never attempted and the station operator receives a nonzero status.

**Watch out:** Adding strict options is only useful when the control flow lets them take effect. An `if` condition handles failures differently from an ordinary command.

**Reread:** The Linux Command Line ch. 27, "Flow Control: Branching with if"; Missing Semester "Shell Tools and Scripting," exit codes and shell scripting.

### E3 — Check station settings (medium, ~15 min)

**Goal:** Tell the operator which settings must be supplied before instrument testing begins.

**Signature:** `bash starter/check_station.sh CONFIG`

`CONFIG` is a readable regular text file. Read it as data; never execute or `source` it (`source` runs a file as shell commands). Required keys, in report order, are `station_id`, `instrument_host`, and `log_dir`. `instrument_host` is the instrument's network name or address; `log_dir` is the directory used for logs. Check presence only; do not connect to the host or check that the directory exists.

Each non-comment line has `key=value`, with no spaces around `=`. Ignore blank lines, lines starting with `#`, and unknown keys. Split at the first `=`; the rest is the literal value, including spaces, additional `=` signs, or shell punctuation. A required key is missing if absent or its final value is empty. Later occurrences replace earlier ones. Whitespace inside a value is preserved and counts as nonempty. Support LF and CRLF (Windows-style line endings), and a final line without a newline. Other malformed input is outside the contract.

When keys are missing, print one `Missing: KEY` line per key in the order above and exit 1. When none are missing, print `Station OK` and a newline, and exit 0. Leave stderr empty for these valid calls.

For a wrong argument count, an unknown option, or a missing/unreadable/non-file `CONFIG`, print `Usage: bash check_station.sh [--json] CONFIG` and a newline to stderr, leave stdout empty, and exit 2. Configuration filenames in this exercise do not start with `-`.

**Example:** A file containing only `station_id=bench-7` prints:

```text
Missing: instrument_host
Missing: log_dir
```

**Watch out:** Use `read -r` to preserve backslashes. An empty value is different from a key that merely appears in a comment. Shell-looking values must stay harmless text.

**Reread:** The Linux Command Line ch. 27, conditional tests, and ch. 32, processing positional parameters; Missing Semester Security and Cryptography, SSH keys (configuration identifies a station; it does not prove its identity).

### E4 — Produce a machine-readable check (medium, ~10 min)

**Goal:** Let an operator tool consume the same result without parsing human messages.

**Signature:** `bash starter/check_station.sh --json CONFIG`

JSON is a text format for structured data. Produce exactly one JSON object on one stdout line, followed by a newline, with exactly two fields: `ok` (a JSON Boolean, a true-or-false value written `true` or `false`) and `missing` (an array of missing key names in E3's order). Spaces between JSON tokens are optional. Apply the same parsing, usage rules, and exit statuses as E3; print no human messages in JSON mode. The option must come before the single config path. Bare `--json` is a usage error.

**Example:** The same incomplete configuration yields `{"ok":false,"missing":["instrument_host","log_dir"]}` with exit 1. A complete file yields `{"ok":true,"missing":[]}` with exit 0.

**Watch out:** JSON strings use double quotes and JSON Booleans are lowercase. Only the three fixed required key names appear in the output, so you do not need a general JSON string escaper.

**Reread:** The Linux Command Line ch. 32, processing options; Missing Semester "Shell Tools and Scripting," composing command-line tools.

## Terminal drill (WSL2 Ubuntu, ~5 min)

This drill is ungraded; its minutes come from the day's readings. Finish E3 first. Use your clone inside Ubuntu's Linux filesystem, starting in the repo root. An **execute permission** allows a file to run as a program. `chmod` changes permissions; `u+x` adds execute permission for the file's owner, and `u-x` removes it.

Create a temporary complete configuration, inspect the script's permissions, then enable and run it directly:

```bash
cd sets/d36
config=$(mktemp /tmp/fasttrack-station.XXXXXX)
printf '%s\n' 'station_id=bench-7' 'instrument_host=127.0.0.1' 'log_dir=/tmp/fasttrack-logs' > "$config"
ls -l starter/check_station.sh
chmod u+x starter/check_station.sh
ls -l starter/check_station.sh
./starter/check_station.sh "$config"
git diff --summary
```

`mktemp` creates a uniquely named temporary file; `$(...)` puts its printed path in the shell variable `config`. `>` writes the configuration into that file. `ls -l` shows permissions in its first column: the owner's execute position changes from `-` to `x`. `./` means run the file at this relative path; its first `#!/usr/bin/env bash` line selects Bash. The completed script prints `Station OK`. `git diff --summary` shows a `mode change` for `sets/d36/starter/check_station.sh`: Git records whether a tracked file is executable.

Remove the permission change afterward so the tests' expectations are unaffected, inspect the restored permissions and Git summary, then remove the temporary configuration and return to the repo root:

```bash
chmod u-x starter/check_station.sh
ls -l starter/check_station.sh
git diff --summary
rm "$config"
cd ../..
```

The script's mode change should disappear from the summary. Your code edits remain. The graded tests invoke `bash script`, so they do not require execute permission; this drill practices the direct invocation an operator uses.
