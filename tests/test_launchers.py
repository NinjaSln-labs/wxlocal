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
    "bootstrap_chat_watch.py",
    "bootstrap_mp_scroll.py",
    "launchers/win/run_daemon.vbs",
]

REMOVED_LEGACY = [
    "run_ninjasin_watchdog.bat",
    "run_mp_idb_watch.bat",
    "run_ninjasin_watchdog.vbs",
    "run_mp_idb_watch.vbs",
    "launch_ninjasin_watchdog.bat",
    "launch_mp_idb_watch.bat",
    "run_daemon.bat",
    "stop_wechat_reader.bat",
    "status_wechat_reader.bat",
    "setup_mp_idb_autostart.bat",
    "stop_ninjasin_watchdog.bat",
    "stop_mp_idb_watch.bat",
    "status_mp_idb_watch.bat",
]


def test_canonical_launchers_exist():
    missing = [name for name in CANONICAL if not (ROOT / name).is_file()]
    assert not missing, f"missing canonical launchers: {missing}"


def test_removed_legacy_launchers_gone():
    still_present = [name for name in REMOVED_LEGACY if (ROOT / name).is_file()]
    assert not still_present, f"legacy launchers should be removed: {still_present}"


def test_stop_wxlocal_uses_daemon_status():
    text = (ROOT / "stop_wxlocal.bat").read_text(encoding="utf-8")
    assert "daemon_status.py stop" in text
    assert "F:\\" not in text


def test_run_bats_use_canonical_bootstraps():
    chat = (ROOT / "run_chat_watch.bat").read_text(encoding="utf-8")
    scroll = (ROOT / "run_mp_scroll.bat").read_text(encoding="utf-8")
    assert "bootstrap_chat_watch.py" in chat
    assert "bootstrap_mp_scroll.py" in scroll
    assert "ninjasin" not in chat.lower()
    assert "mp_idb" not in scroll.lower()


def test_autostart_spawns_canonical_bootstraps():
    text = (ROOT / "bootstrap_autostart.py").read_text(encoding="utf-8")
    assert "bootstrap_chat_watch.py" in text
    assert "bootstrap_mp_scroll.py" in text
    assert "bootstrap_ninjasin_watch.py" not in text
