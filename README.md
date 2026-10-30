# Fasttrack exercises

Small test-driven exercise sets that go with the Engineering Tracker. Each set practices the Python and test-station skills taught by that day. You write the code; the tests tell you what's right.

## Set up once (about 15 minutes)

**Codespaces option:** on this repo's GitHub page choose **Code → Codespaces → Create codespace**. No local installs are needed; skip steps 1-4 below and start at step 5. It opens VS Code with Python and the tools installed, running Linux in your browser. This is recommended for the Linux and shell days: the commands run in a real Linux environment.

1. **Install VS Code** and, from its Extensions panel, the **Python** extension by Microsoft.
2. **Install Python 3.12 or newer.** On Windows, tick **Add Python to PATH** in the installer, then reopen VS Code. On Linux or Mac, check `python3 --version`; Linux may also need the distribution's `python3-venv` package.
3. **Install Git.** On Windows, download [Git for Windows](https://git-scm.com/download/win), run the installer, and keep the option to use Git from the command line. Reopen VS Code after installation so its terminals can find Git. On Linux or Mac, install Git if `git --version` is not available.
4. **Get the exercises:** in VS Code choose **Terminal → New Terminal** (use PowerShell on Windows). In that terminal, run `git clone https://github.com/derrickdove/fasttrack-exercises.git`, then in VS Code choose **File → Open Folder** on `fasttrack-exercises`. After this, `git pull` gets new sets.
5. **Prove it works:** press **Ctrl+Shift+B** (Cmd+Shift+B on Mac) and choose **Test: d00-hello**. The first run creates `.venv`, a local folder holding Python and the exercise tools, and installs the tools automatically. It needs internet and can take a few minutes. You should see `Exercises: 1 / 1 passed`.

Use Ctrl+Shift+B to run a set's tests. Save your changes before running. You don't need to activate `.venv` or install packages by hand.

## Doing a set

1. Keep the whole `fasttrack-exercises` folder open as your VS Code workspace. Choose **Terminal → New Terminal** and run `git pull` there. In VS Code's Explorer panel, expand the set directory (for example `sets/d05/`) and open its `README.md`.
2. Write your code in the files it names, usually `starter/*.py`. Don't edit `tests/`.
3. Press **Ctrl+Shift+B** and choose **Test: d05** (or whichever set). Red means not yet; fix and rerun after each exercise.
4. Report **all pass / partial / stuck** on the task in the tracker. Partial and stuck come back in two days. After you report, the tracker links the reference solution so you can compare approaches.

From a terminal you can also run `powershell -NoProfile -ExecutionPolicy Bypass -File tools\run.ps1 d05` on Windows or `bash tools/run.sh d05` on Linux or Mac. The scripts work from any folder when you give the script's full path.

## Reading results

`Exercises: 3 / 5 passed` means three exercises are correct. An exercise may have several tests; all of them must pass. The lines above the total name each exercise and show its first failure. `NotImplementedError: E2: ...` means that exercise still has its supplied unfinished body.

**Your code could not be loaded:** means a file doesn't load, often because of an import error (Python cannot find a name or module) or a syntax error (Python cannot read a statement). Fix that error first. The report counts zero passes until the files load. `0 / ?` means no test names could be found. A skipped test counts as unfinished.

## Capstone and gates

Build the chassis tester in `capstone/` as the tracker introduces each block.
Press **Ctrl+Shift+B → Gate: b1** (later **Gate: b2** through **Gate: b6**); tasks appear when those suites arrive.
Gates run every earlier block too and finish with `Checks: N / M passed`.

## Troubleshooting

- **Scripts are blocked** (Windows): the task already uses `-ExecutionPolicy Bypass`. In a terminal use the full PowerShell command above. If your company laptop still blocks it, use a Codespace.
- **Python not found:** install Python 3.12+, enable Add Python to PATH on Windows, and reopen VS Code. Check `python --version` on Windows or `python3 --version` on Linux or Mac. If Python is installed elsewhere, set `FT_PYTHON` to its executable's full path before the first run.
- **The tools could not be installed:** check your connection and rerun. An interrupted install is retried automatically.
- **Paths with spaces or OneDrive:** spaces are fine. If OneDrive locks files in `.venv`, close the terminals and put your clone in a local folder such as `C:\git\fasttrack-exercises`, then run again.
- **Changing computers or operating systems:** delete `.venv` and rerun the task. Python environments belong to the machine that created them.

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
