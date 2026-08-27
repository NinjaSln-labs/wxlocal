"""WeChat local data directory configuration."""
from __future__ import annotations

import os
from pathlib import Path

from env_loader import load_env
from paths import DECRYPTED_DIR as _DECRYPTED_DIR
from paths import OUTPUT_DIR as _OUTPUT_DIR

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
OUTPUT_DIR = str(_OUTPUT_DIR)
DECRYPTED_DIR = str(_DECRYPTED_DIR)
