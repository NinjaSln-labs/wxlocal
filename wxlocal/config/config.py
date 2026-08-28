"""WeChat local data directory configuration."""
from __future__ import annotations

import os
from pathlib import Path

from wxlocal.config.env_loader import load_env

load_env()

from wxlocal.config.paths import DECRYPTED_DIR as _DECRYPTED_DIR  # noqa: E402
from wxlocal.config.paths import OUTPUT_DIR as _OUTPUT_DIR  # noqa: E402


def _default_data_root() -> str:
    env = os.environ.get("WECHAT_DATA_ROOT", "").strip()
    if env:
        return env
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        candidate = Path(local) / "Tencent" / "xwechat" / "xwechat_files"
        if candidate.is_dir():
            return str(candidate)
    return ""


def find_user_db_storage(data_root: str | Path | None = None) -> Path | None:
    root = Path(data_root or DATA_ROOT)
    if not root.is_dir():
        return None
    for name in os.listdir(root):
        if name in ("all_users", "Backup"):
            continue
        db_storage = root / name / "db_storage"
        if db_storage.is_dir():
            return db_storage
    return None


DATA_ROOT = _default_data_root()
OUTPUT_DIR = str(_OUTPUT_DIR)
DECRYPTED_DIR = str(_DECRYPTED_DIR)
