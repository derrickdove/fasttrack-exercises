from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

# The supplied checks run this file separately against good and broken helpers.
collect_ignore = ["starter/test_review2_learner.py"]
