#!/usr/bin/env bash
# macOS / Linux / Codespaces / Git Bash: bash tools/run.sh d05
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ID="${1:-}"
targets=()
if [[ -n "$ID" && "$ID" != . && "$ID" != .. && "$ID" != */* && "$ID" != *\\* && -d "sets/$ID" ]]; then
  targets=("sets/$ID")
  unset FT_REPORT_MODE
elif [[ "$ID" =~ ^b[1-6]$ && -d "gates/$ID" ]]; then
  for ((n=1; n<=${ID#b}; n++)); do
    if [[ ! -d "gates/b$n" ]]; then
      echo "Missing earlier gate b$n. Get the latest sets with git pull."
      exit 1
    fi
    targets+=("gates/b$n")
  done
  export FT_REPORT_MODE=checks
  export FT_CAPSTONE="${FT_CAPSTONE:-$ROOT/capstone}"
else
  echo "No set or gate named '$ID'. Choose one of these:"
  echo 'Sets:'
  for folder in sets/*/; do [[ ! -d "$folder" ]] || echo "  $(basename "$folder")"; done
  echo 'Gates (available as blocks are added):'
  for folder in gates/b[1-6]/; do [[ ! -d "$folder" ]] || echo "  $(basename "$folder")"; done
  exit 1
fi
PLATFORM="$(uname -s)"
PYTHON="$ROOT/.venv/bin/python"
if [[ "$PLATFORM" == Linux* ]]; then
  if [[ ! -f "$PYTHON" && -f "$ROOT/.venv/Scripts/python.exe" ]]; then
    echo 'This .venv was created on Windows and cannot be used on Linux.'
    echo 'Make a fresh Linux clone under ~/src, or delete .venv and run this command again.'
    exit 1
  fi
elif [[ ! -f "$PYTHON" && -f "$ROOT/.venv/Scripts/python.exe" ]]; then
  # Git Bash can reuse the Windows venv created by run.ps1.
  PYTHON="$ROOT/.venv/Scripts/python.exe"
fi
# C++ sets use the shared compiler/report hook, without Python package setup.
if compgen -G "sets/$ID/tests/*.cpp" >/dev/null; then
  for candidate in "${FT_PYTHON:-}" "$PYTHON" python3 python; do
    [[ "$PLATFORM" != Linux* || "$candidate" != */Scripts/python.exe ]] || continue
    [[ -n "$candidate" ]] || continue
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
      if "$candidate" "$ROOT/tools/verify_sets.py" --run-cpp "$ID"; then exit 0; fi
      exit 1
    fi
  done
  echo 'Python 3.12+ was not found. Install Python or set FT_PYTHON to its executable.'
  exit 1
fi
if [[ ! -f "$PYTHON" ]]; then
  echo 'Creating .venv (your local Python environment) ...'
  found=false
  for candidate in "${FT_PYTHON:-python3}" python python3; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
      "$candidate" -m venv "$ROOT/.venv" || exit 1
      found=true
      break
    fi
  done
  if [[ "$found" != true ]]; then
    echo 'Python 3.12+ was not found. Install Python, then reopen VS Code.'
    exit 1
  fi
  if [[ "$PLATFORM" != Linux* && ! -f "$PYTHON" && -f "$ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON="$ROOT/.venv/Scripts/python.exe"
  fi
fi
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo 'This .venv needs Python 3.12+. Delete .venv and run again with Python 3.12+ installed.'
  exit 1
fi
STAMP="$ROOT/.venv/requirements.stamp"
if [[ ! -f "$STAMP" || requirements.txt -nt "$STAMP" ]]; then
  echo 'Installing the exercise tools (the first run can take a few minutes) ...'
  if ! "$PYTHON" -m pip install --disable-pip-version-check -r requirements.txt; then
    echo 'The tools could not be installed. Check your internet connection, then run again.'
    exit 1
  fi
  printf '%s\n' 'Requirements installed successfully.' > "$STAMP"
fi
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS=''
if "$PYTHON" -m pytest "${targets[@]}" -p tools.ft_report -q --no-header --rootdir "$ROOT"; then
  exit 0
fi
exit 1
