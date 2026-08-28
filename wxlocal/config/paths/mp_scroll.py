"""mp-scroll (IndexedDB watch) paths and PID/log filenames."""
from __future__ import annotations

from wxlocal.config.paths.kb import WECHAT_KB

MP_SCROLL_KB = WECHAT_KB / "mp-scroll"
MP_SCROLL_EXPORT = MP_SCROLL_KB / "exports"
MP_SCROLL_ARCHIVE = MP_SCROLL_KB / "archive"
MP_SCROLL_OCR_DIR = MP_SCROLL_KB / "ocr"
MP_SCROLL_STATE_DIR = MP_SCROLL_KB / "state"

MP_SCROLL_PID = MP_SCROLL_STATE_DIR / "mp_scroll.pid"
LEGACY_MP_SCROLL_PID = MP_SCROLL_STATE_DIR / "mp_idb_watch.pid"

MP_SCROLL_WATCH_LOG = MP_SCROLL_STATE_DIR / "mp_scroll.log"
LEGACY_MP_SCROLL_WATCH_LOG = MP_SCROLL_STATE_DIR / "mp_idb_watch.log"
MP_SCROLL_ERROR_LOG = MP_SCROLL_STATE_DIR / "mp_scroll_errors.log"
LEGACY_MP_SCROLL_ERROR_LOG = MP_SCROLL_STATE_DIR / "mp_idb_watch_errors.log"
MP_SCROLL_LAUNCH_LOG = MP_SCROLL_STATE_DIR / "launch.log"


def ensure_mp_scroll_dirs() -> None:
    MP_SCROLL_EXPORT.mkdir(parents=True, exist_ok=True)
    MP_SCROLL_ARCHIVE.mkdir(parents=True, exist_ok=True)
    MP_SCROLL_OCR_DIR.mkdir(parents=True, exist_ok=True)
    MP_SCROLL_STATE_DIR.mkdir(parents=True, exist_ok=True)
