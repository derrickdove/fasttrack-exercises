# Fasttrack exercises

Small test-driven exercise sets that go with the Engineering Tracker. Each set practices the Python and test-station skills taught by that day. You write the code; the tests tell you what's right.

## Set up once (WSL2 Ubuntu 24.04, about 50 minutes)

**WSL2** (Windows Subsystem for Linux 2) runs Linux inside Windows so you can use Ubuntu's programs and terminal alongside your Windows apps. **Bash** is the shell, the program that reads the commands you type; use it for everyday exercise work. **PATH** lists the folders searched for commands.

1. **Install Ubuntu 24.04.** Open Windows PowerShell as administrator and run:

   ```powershell
   wsl --set-default-version 2
   wsl --install -d Ubuntu-24.04
   ```

   Restart Windows if requested, open **Ubuntu 24.04** from Start, and create your Ubuntu username and password. In PowerShell, `wsl --list --verbose` should show `Ubuntu-24.04` using version `2`.
2. **Install VS Code on Windows** and the **Remote-WSL** extension by Microsoft. An extension adds features to the editor; Remote-WSL lets it open files and run tools inside Ubuntu. From PowerShell you can install it with `code --install-extension ms-vscode-remote.remote-wsl`.
3. **Install the Linux tools.** In the Ubuntu terminal, run:

   ```bash
   sudo apt-get update && sudo apt-get install -y python3 python3-venv git build-essential tcpdump openssh-server iproute2 curl less procps
   ```

   `sudo` runs a command as the Linux administrator; enter your Ubuntu password when asked (typing it shows no characters). `apt-get` installs Ubuntu packages. This supplies Python and its environment support, Git (which tracks code changes), `build-essential` (including `g++`, a compiler that turns C++ code into a program), and the network and process tools used later in the plan.
4. **Check systemd**, the Linux manager that starts and supervises services (programs that run in the background):

   ```bash
   ps -p 1 -o comm=
   ```

   This prints the name of the first Linux process. If it is not `systemd`, run `sudoedit /etc/wsl.conf` to edit WSL's settings. Keep any existing settings; add a `[boot]` section if absent, then add or change its `systemd` line so that section contains:

   ```ini
   [boot]
   systemd=true
   ```

   If asked to choose an editor, choose nano; in nano, save with **Ctrl+O**, **Enter**, then exit with **Ctrl+X**. From **Windows PowerShell**, run `wsl --shutdown`, then reopen Ubuntu and check `ps -p 1 -o comm=` again. It must print `systemd` for the day-41 service drill.
5. **Clone fresh inside Linux.** A clone is your local copy of this Git repository, the project and its change history. Use your Linux home directory (`~`), not a Windows clone under `/mnt/c`; do not reuse or copy a Windows `.venv`.

   ```bash
   mkdir -p ~/src && cd ~/src && git clone https://github.com/derrickdove/fasttrack-exercises.git
   cd fasttrack-exercises
   code .
   ```

   `mkdir -p` creates the directory if needed; `cd` changes directory; `code .` opens the current folder in VS Code. Check the bottom-left connection indicator says **WSL: Ubuntu-24.04**. Install Microsoft's **Python** extension in that WSL window when prompted or through Extensions.
6. **Prove it works.** In that VS Code window choose **Terminal → New Terminal**; it should open Bash in your Linux clone. Run:

   ```bash
   bash tools/run.sh d00-hello
   ```

   The first run creates `.venv`, a local folder holding Python and the exercise tools, and installs the tools automatically. It needs internet and can take a few minutes. Expect `Exercises: 1 / 1 passed`: this setup check is already correct. You don't need to activate `.venv` or install Python packages by hand.

**Alternative — native Windows (PowerShell):** install VS Code with Microsoft's Python extension, Python 3.12+ (tick **Add Python to PATH**), and [Git for Windows](https://git-scm.com/download/win). Reopen VS Code, clone the repo into a local Windows folder such as `C:\git`, and open it. In its PowerShell terminal run `powershell -NoProfile -ExecutionPolicy Bypass -File tools\run.ps1 d00-hello`. This uses a separate Windows `.venv`. See d48's compiler note for Visual Studio Build Tools. Use WSL for Linux practice, including the day-41 systemd drill.

**Alternative — Codespaces:** if WSL installation exceeds the setup time, on this repo's GitHub page choose **Code → Codespaces → Create codespace**. It opens VS Code with Linux and the tools installed in your browser; run `bash tools/run.sh d00-hello` there. Its free tier is about **60 hours/month on 2 cores** (two processing units). Codespaces cannot run the day-41 systemd drill; use WSL for that drill.

## Doing a set

1. Keep the whole `fasttrack-exercises` folder open in the WSL VS Code window. In **Terminal → New Terminal**, run `git pull` to get new sets, then open the day's README (for example `sets/d05/README.md`).
2. Start with `pwd` to print your current directory and `git status --short` to list changed files. Write your code in the files the set names, usually `starter/*.py`. Don't edit `tests/`.
3. Save your changes and run `bash tools/run.sh d05` (replace `d05` with the current set). Red means not yet; fix and rerun after each exercise. Run `git diff` to review your edits.
4. Report **all pass / partial / stuck** on the task in the tracker. Partial and stuck come back in two days. After you report, the tracker links the reference solution so you can compare approaches.

Use this Bash loop from the repo folder every day; replace `<set>` with a name such as `d05`, without the angle brackets:

```bash
pwd
git status --short
bash tools/run.sh <set>
git diff
```

Use the first five minutes of the existing code/test/retry time for this loop; no extra study time is needed. **Ctrl+Shift+B → Test: d05** is a shortcut to the same runner. In native Windows PowerShell use `powershell -NoProfile -ExecutionPolicy Bypass -File tools\run.ps1 d05` for the test command. The scripts also work from another folder if you give the script's full path.

## Reading results

`Exercises: 3 / 5 passed` means three exercises are correct. An exercise may have several tests; all of them must pass. The lines above the total name each exercise and show its first failure. `NotImplementedError: E2: ...` means that exercise still has its supplied unfinished body.

**Your code could not be loaded:** means a file doesn't load, often because of an import error (Python cannot find a name or module) or a syntax error (Python cannot read a statement). Fix that error first. The report counts zero passes until the files load. `0 / ?` means no test names could be found. A skipped test counts as unfinished.

## Capstone and gates

Build the chassis tester in `capstone/` as the tracker introduces each block.
A **gate** is a group of checks for a capstone block. Use the same Bash loop with `bash tools/run.sh b1` (later `b2` through `b6`). Gates run every earlier block too and finish with `Checks: N / M passed`. **Ctrl+Shift+B → Gate: b1** is a shortcut; tasks appear when those suites arrive.

On capstone-only days, use `(cd capstone && ../.venv/bin/python -m pytest)` for the test command (native Windows PowerShell: `cd capstone`, `..\.venv\Scripts\python.exe -m pytest`, then `cd ..`); it runs your capstone tests with the Python environment created during setup. On review days, rerun the selected retry set, review set, or gate in the same loop.

## Troubleshooting

- **Scripts are blocked** (Windows): the task already uses `-ExecutionPolicy Bypass`. In a terminal use the full PowerShell command above. If your company laptop still blocks it, use a Codespace.
- **Python not found or environment creation fails:** in WSL, rerun the Ubuntu package command above and check `python3 --version` is 3.12+. In native Windows, install Python 3.12+, enable **Add Python to PATH**, reopen VS Code, and check `python --version`. If Python is installed elsewhere, set `FT_PYTHON`, an environment variable (a named setting passed to programs), to its executable's full path before the first run.
- **The tools could not be installed:** check your connection and rerun. An interrupted install is retried automatically.
- **Paths with spaces or OneDrive:** spaces are fine. If OneDrive locks files in `.venv`, close the terminals and put your clone in a local folder such as `C:\git\fasttrack-exercises`, then run again.
- **Windows `.venv` found in Linux:** make a fresh clone under `~/src` as above, or delete only `.venv` and rerun `bash tools/run.sh d00-hello` to create a Linux environment. Python environments belong to the operating system and machine that created them. Keep Windows and Linux clones separate.
- **Instrument or packet tools:** d17/d19 use simulated instruments (software substitutes); d22 uses serial loopback (sent bytes come back to the same program). These tests need no vendor instrument drivers, access to physical USB devices, or changes to serial-device permissions. d30 reads a supplied packet-capture file and needs no capture permission. d36's tests run Bash commands; d41's automated tests read service text, while its live drill needs the running systemd checked above.

## Layout

```text
sets/d00-hello/       setup check (already correct)
sets/d01/ …          one folder per daily set
sets/r1/ …           review sets
sets/check34/ …      longer checkpoints
  README.md          what to do, exact contracts, readings to reread
  starter/           your code
  tests/             the tests (don't edit)
  conftest.py         tells Python where this set's files live
  data/              supplied measurements or instrument files, when needed
capstone/chassis/    the chassis tester you build across the plan
capstone/tests/      your own capstone tests
gates/               supplied checks for each capstone block
tools/run.ps1        Windows runner
tools/run.sh         Linux / Mac / Codespaces / Git Bash runner
```

Authors: run `.venv\Scripts\python tools\verify_sets.py <id> --repeat 3 --mypy` (Linux: `.venv/bin/python`). It checks isolated starter and reference copies; references default to the sibling `fasttrack-exercises-solutions` repo. Run `python tools/gen_tasks.py` after adding folders. `.verify.json` supports `{"starter_expect": "all"}` for setup checks; the default is `"none"`, with every failure required to be `NotImplementedError`. A set-level `mypy.ini` can relax checks for named helper modules using per-module sections. `FT_CAPSTONE` selects another capstone directory for gates. To check the shared tools, run `.venv\Scripts\python -m unittest discover -s tools -p test_scaffold.py`.
