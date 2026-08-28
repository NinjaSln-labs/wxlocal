"""Repo-local runtime paths (output, decrypt cache)."""
from __future__ import annotations

from pathlib import Path

from wxlocal.config.paths.kb import ROOT


OUTPUT_DIR = ROOT / "output"
DECRYPTED_DIR = OUTPUT_DIR / "decrypted"
LEGACY_DECRYPTED_DIR = ROOT / "decrypted"


def ensure_output_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def ensure_decrypted_dir() -> Path:
    """Canonical decrypt cache: output/decrypted. Migrates repo-root decrypted/ once."""
    ensure_output_dirs()
    canonical = DECRYPTED_DIR
    legacy = LEGACY_DECRYPTED_DIR
    if canonical.is_dir() and (canonical / "message").is_dir():
        return canonical
    if legacy.is_dir() and (legacy / "message").is_dir():
        if not canonical.exists():
            import shutil

            shutil.move(str(legacy), str(canonical))
            return canonical
        if (canonical / "message").is_dir():
            return canonical
        return legacy
    canonical.mkdir(parents=True, exist_ok=True)
    return canonical
