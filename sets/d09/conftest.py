from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

# The grading tests run this file in isolated pytest processes themselves.
collect_ignore = ["starter/test_limits_learner.py"]
