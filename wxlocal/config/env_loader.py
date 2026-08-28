"""Load repo-root `.env` into os.environ (no external dependency)."""
from __future__ import annotations

import os
from pathlib import Path

from wxlocal.config._root import PROJECT_ROOT

_LOADED = False
ROOT = PROJECT_ROOT


def load_env(env_path: Path | None = None) -> None:
    global _LOADED
    if _LOADED:
        return
    path = env_path or ROOT / ".env"
    if not path.is_file():
        _LOADED = True
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)
    _LOADED = True
