"""Print one env var from repo-root `.env` (for batch launchers)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from env_loader import load_env

load_env()

key = sys.argv[1]
default = sys.argv[2] if len(sys.argv) > 2 else ""
print(os.environ.get(key, default).strip())
