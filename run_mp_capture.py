"""Shim — use scripts/ops/run_mp_capture.py."""
from pathlib import Path
import runpy
import sys

_OPS = Path(__file__).resolve().parent / "scripts" / "ops" / "run_mp_capture.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))
runpy.run_path(str(_OPS), run_name="__main__")
