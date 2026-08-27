"""WeChat local data directory configuration."""
from __future__ import annotations

import os
from pathlib import Path

from env_loader import load_env

load_env()

_ROOT = Path(__file__).resolve().parent


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


DATA_ROOT = _default_data_root()
OUTPUT_DIR = os.path.join(_ROOT, "output")
DECRYPTED_DIR = os.path.join(OUTPUT_DIR, "decrypted")
