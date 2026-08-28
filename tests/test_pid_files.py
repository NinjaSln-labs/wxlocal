"""PID file naming and migration (R5)."""
from __future__ import annotations

from pathlib import Path

from wxlocal.config.paths import (
    CHAT_WATCH_PID,
    LEGACY_CHAT_WATCH_PID,
    LEGACY_MP_SCROLL_PID,
    MP_SCROLL_PID,
)
from wxlocal.shared.daemon import acquire_pid_lock, migrate_pid_file


def test_canonical_pid_constants():
    assert CHAT_WATCH_PID.name == "chat_watch.pid"
    assert MP_SCROLL_PID.name == "mp_scroll.pid"
    assert LEGACY_CHAT_WATCH_PID.name == "ninjasin_watch.pid"
    assert LEGACY_MP_SCROLL_PID.name == "mp_idb_watch.pid"


def test_migrate_pid_file_renames_legacy(tmp_path: Path):
    canonical = tmp_path / "chat_watch.pid"
    legacy = tmp_path / "ninjasin_watch.pid"
    legacy.write_text("12345", encoding="utf-8")

    migrate_pid_file(canonical, legacy)

    assert canonical.read_text(encoding="utf-8") == "12345"
    assert not legacy.exists()


def test_acquire_pid_lock_migrates_legacy(tmp_path: Path):
    canonical = tmp_path / "mp_scroll.pid"
    legacy = tmp_path / "mp_idb_watch.pid"
    legacy.write_text("99999", encoding="utf-8")

    assert acquire_pid_lock(canonical, legacy_pid_files=(legacy,)) is True
    assert canonical.is_file()
    assert not legacy.exists()
