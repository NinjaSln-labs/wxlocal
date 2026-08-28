"""mitm mp-capture paths."""
from __future__ import annotations

from wxlocal.config.paths.kb import WECHAT_KB

MP_CAPTURE_KB = WECHAT_KB / "mp-capture"
MP_CAPTURE_EXPORT = MP_CAPTURE_KB / "exports"
MP_CAPTURE_ARCHIVE = MP_CAPTURE_KB / "archive"
MP_CAPTURE_RAW = MP_CAPTURE_KB / "raw"
MP_CAPTURE_REGISTRY = MP_CAPTURE_KB / "registry" / "idb_registry.json"


def ensure_mp_capture_dirs() -> None:
    MP_CAPTURE_EXPORT.mkdir(parents=True, exist_ok=True)
    MP_CAPTURE_ARCHIVE.mkdir(parents=True, exist_ok=True)
    MP_CAPTURE_RAW.mkdir(parents=True, exist_ok=True)
    MP_CAPTURE_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
