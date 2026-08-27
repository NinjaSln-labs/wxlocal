"""Knowledge-base and runtime paths.

Environment:
  WECHAT_KB_ROOT        Root dir containing `wechat/` subfolders (default: ./data/knowledge-base)
  WECHAT_WATCH_CONTACT  Contact for chat-watch pipeline (default: FileTransfer)
"""
from __future__ import annotations

import os
from pathlib import Path

from env_loader import load_env

load_env()

ROOT = Path(__file__).resolve().parent
_DEFAULT_KB = ROOT / "data" / "knowledge-base"


def _resolve_kb_root() -> Path:
    env = os.environ.get("WECHAT_KB_ROOT", "").strip()
    if env:
        return Path(env)
    return _DEFAULT_KB


KB_ROOT = _resolve_kb_root()
WECHAT_KB = KB_ROOT / "wechat"

# Chat watch (export one pinned contact)
WATCH_CONTACT = os.environ.get("WECHAT_WATCH_CONTACT", "FileTransfer")
NINJASIN_CONTACT = WATCH_CONTACT  # backward-compat alias

# Historical folder name `ninjasin/` — works for any contact when WECHAT_WATCH_CONTACT is set
CHAT_WATCH_KB = WECHAT_KB / "chat-watch"
NINJASIN_KB = WECHAT_KB / "ninjasin"  # legacy path; used if chat-watch/ absent
WENJIN_NINJASIN_KB = NINJASIN_KB  # backward-compat alias


def _chat_watch_root() -> Path:
    if CHAT_WATCH_KB.is_dir():
        return CHAT_WATCH_KB
    return NINJASIN_KB


_CHAT_ROOT = _chat_watch_root()
ARCHIVE_ROOT = _CHAT_ROOT / "archive"
CURATED_DIR = _CHAT_ROOT / "curated"
EXPORTS_DIR = _CHAT_ROOT / "exports"
NINJASIN_STATE_DIR = _CHAT_ROOT / "state"
NINJASIN_DAEMON_LOG = NINJASIN_STATE_DIR / "chat_watch.log"
NINJASIN_ERROR_LOG = NINJASIN_STATE_DIR / "chat_watch_errors.log"
NINJASIN_LAUNCH_LOG = NINJASIN_STATE_DIR / "launch.log"

# Official account · dev-filter corpus
MP_DEV_KB = WECHAT_KB / "mp-dev"
MP_DEV_EXPORT = MP_DEV_KB / "exports"
MP_DEV_ARCHIVE = MP_DEV_KB / "archive"

# Official account · mitm capture
MP_CAPTURE_KB = WECHAT_KB / "mp-capture"
MP_CAPTURE_EXPORT = MP_CAPTURE_KB / "exports"
MP_CAPTURE_ARCHIVE = MP_CAPTURE_KB / "archive"
MP_CAPTURE_RAW = MP_CAPTURE_KB / "raw"
MP_CAPTURE_REGISTRY = MP_CAPTURE_KB / "registry" / "idb_registry.json"

# Official account · scroll-feed pipeline (IndexedDB watch)
MP_SCROLL_KB = WECHAT_KB / "mp-scroll"
MP_SCROLL_EXPORT = MP_SCROLL_KB / "exports"
MP_SCROLL_ARCHIVE = MP_SCROLL_KB / "archive"
MP_SCROLL_OCR_DIR = MP_SCROLL_KB / "ocr"
MP_SCROLL_STATE_DIR = MP_SCROLL_KB / "state"
MP_SCROLL_WATCH_LOG = MP_SCROLL_STATE_DIR / "mp_idb_watch.log"
MP_SCROLL_ERROR_LOG = MP_SCROLL_STATE_DIR / "mp_idb_watch_errors.log"
MP_SCROLL_LAUNCH_LOG = MP_SCROLL_STATE_DIR / "launch.log"

# Repo-local runtime (keys, decrypt cache, daemon logs)
OUTPUT_DIR = ROOT / "output"


def ensure_kb_dirs() -> None:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    NINJASIN_STATE_DIR.mkdir(parents=True, exist_ok=True)


def ensure_mp_dev_dirs() -> None:
    MP_DEV_EXPORT.mkdir(parents=True, exist_ok=True)
    MP_DEV_ARCHIVE.mkdir(parents=True, exist_ok=True)


def ensure_mp_capture_dirs() -> None:
    MP_CAPTURE_EXPORT.mkdir(parents=True, exist_ok=True)
    MP_CAPTURE_ARCHIVE.mkdir(parents=True, exist_ok=True)
    MP_CAPTURE_RAW.mkdir(parents=True, exist_ok=True)
    MP_CAPTURE_REGISTRY.parent.mkdir(parents=True, exist_ok=True)


def ensure_mp_scroll_dirs() -> None:
    MP_SCROLL_EXPORT.mkdir(parents=True, exist_ok=True)
    MP_SCROLL_ARCHIVE.mkdir(parents=True, exist_ok=True)
    MP_SCROLL_OCR_DIR.mkdir(parents=True, exist_ok=True)
    MP_SCROLL_STATE_DIR.mkdir(parents=True, exist_ok=True)


def default_radium_profiles() -> Path:
    """WeChat PC Chromium profile root (%LOCALAPPDATA%\\...\\radium\\web\\profiles)."""
    override = os.environ.get("WECHAT_RADIUM_PROFILES", "").strip()
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        return Path(local) / "Tencent" / "xwechat" / "radium" / "web" / "profiles"
    return Path.home() / "AppData" / "Roaming" / "Tencent" / "xwechat" / "radium" / "web" / "profiles"
