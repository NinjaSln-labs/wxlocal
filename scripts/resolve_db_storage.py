"""Print db_storage path from WECHAT_DATA_ROOT (for run_extract.bat)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DATA_ROOT, find_user_db_storage

db_storage = find_user_db_storage(DATA_ROOT)
if not db_storage:
    sys.exit(1)
print(db_storage)
