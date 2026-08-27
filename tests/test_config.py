"""Ensure .env.example documents env vars used by runtime entrypoints."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = REPO_ROOT / ".env.example"

RUNTIME_FILES = [
    REPO_ROOT / "config.py",
    REPO_ROOT / "paths.py",
    REPO_ROOT / "watchdog.py",
    REPO_ROOT / "watch_mp_idb.py",
    REPO_ROOT / "WxLocalAutostart.vbs",
    REPO_ROOT / "run_mp_idb_watch.vbs",
    REPO_ROOT / "run_ninjasin_watchdog.vbs",
]


def _parse_env_example_keys() -> set[str]:
    keys: set[str] = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, _ = line.partition("=")
        key = key.strip()
        if key:
            keys.add(key)
    return keys


def test_env_example_keys_are_referenced_in_runtime():
    keys = _parse_env_example_keys()
    corpus = "\n".join(path.read_text(encoding="utf-8") for path in RUNTIME_FILES)
    missing = sorted(k for k in keys if k not in corpus)
    assert not missing, f".env.example keys not referenced in runtime files: {missing}"
