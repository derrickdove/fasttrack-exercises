"""Point gates at the learner's capstone, or an isolated reference copy."""
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(os.environ.get("FT_CAPSTONE", str(REPO / "capstone"))).resolve()))
