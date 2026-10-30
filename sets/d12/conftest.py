from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

# The outer suite grades the learner's tests in isolated pytest subprocesses.
collect_ignore = ["starter"]
