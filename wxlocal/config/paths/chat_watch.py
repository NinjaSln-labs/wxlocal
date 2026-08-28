"""Chat-watch pipeline paths and PID/log filenames."""
from __future__ import annotations

import os

from wxlocal.config.paths.kb import WECHAT_KB

WATCH_CONTACT = os.environ.get("WECHAT_WATCH_CONTACT", "FileTransfer")
NINJASIN_CONTACT = WATCH_CONTACT  # backward-compat alias

CHAT_WATCH_KB = WECHAT_KB / "chat-watch"
NINJASIN_KB = WECHAT_KB / "ninjasin"
WENJIN_NINJASIN_KB = NINJASIN_KB


def _chat_watch_root():
    if CHAT_WATCH_KB.is_dir():
        return CHAT_WATCH_KB
    return NINJASIN_KB


_CHAT_ROOT = _chat_watch_root()
ARCHIVE_ROOT = _CHAT_ROOT / "archive"
CURATED_DIR = _CHAT_ROOT / "curated"
EXPORTS_DIR = _CHAT_ROOT / "exports"
NINJASIN_STATE_DIR = _CHAT_ROOT / "state"

CHAT_WATCH_PID = NINJASIN_STATE_DIR / "chat_watch.pid"
LEGACY_CHAT_WATCH_PID = NINJASIN_STATE_DIR / "ninjasin_watch.pid"

NINJASIN_DAEMON_LOG = NINJASIN_STATE_DIR / "chat_watch.log"
NINJASIN_ERROR_LOG = NINJASIN_STATE_DIR / "chat_watch_errors.log"
NINJASIN_LAUNCH_LOG = NINJASIN_STATE_DIR / "launch.log"


def ensure_kb_dirs() -> None:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    NINJASIN_STATE_DIR.mkdir(parents=True, exist_ok=True)
