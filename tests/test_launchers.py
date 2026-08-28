"""Smoke tests for canonical launcher entrypoints."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CANONICAL = [
    "run_chat_watch.bat",
    "run_mp_scroll.bat",
    "run_extract.bat",
    "stop_wxlocal.bat",
    "status_wxlocal.bat",
    "setup_wxlocal_autostart.bat",
    "WxLocalAutostart.vbs",
    "bootstrap_autostart.py",
    "launchers/win/run_daemon.vbs",
]

REMOVED_LEGACY = [
    "run_ninjasin_watchdog.bat",
    "run_mp_idb_watch.bat",
    "launch_ninjasin_watchdog.bat",
    "launch_mp_idb_watch.bat",
    "run_daemon.bat",
    "stop_wechat_reader.bat",
    "status_wechat_reader.bat",
    "setup_mp_idb_autostart.bat",
]


def test_canonical_launchers_exist():
    missing = [name for name in CANONICAL if not (ROOT / name).is_file()]
    assert not missing, f"missing canonical launchers: {missing}"


def test_removed_legacy_launchers_gone():
    still_present = [name for name in REMOVED_LEGACY if (ROOT / name).is_file()]
    assert not still_present, f"legacy launchers should be removed: {still_present}"


def test_stop_bats_use_daemon_status():
    for name in ("stop_wxlocal.bat", "stop_mp_idb_watch.bat", "stop_ninjasin_watchdog.bat"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "daemon_status.py stop" in text
        assert "F:\\" not in text
