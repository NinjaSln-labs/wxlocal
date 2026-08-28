"""Knowledge-base root resolution."""
from __future__ import annotations

import os
from pathlib import Path

from wxlocal.config._root import PROJECT_ROOT
from wxlocal.config.env_loader import load_env

load_env()

ROOT = PROJECT_ROOT
_DEFAULT_KB = ROOT / "data" / "knowledge-base"


def _resolve_kb_root() -> Path:
    env = os.environ.get("WECHAT_KB_ROOT", "").strip()
    if env:
        return Path(env)
    return _DEFAULT_KB


KB_ROOT = _resolve_kb_root()
WECHAT_KB = KB_ROOT / "wechat"
