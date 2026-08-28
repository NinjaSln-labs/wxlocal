"""mp-dev corpus paths."""
from __future__ import annotations

from wxlocal.config.paths.kb import WECHAT_KB

MP_DEV_KB = WECHAT_KB / "mp-dev"
MP_DEV_EXPORT = MP_DEV_KB / "exports"
MP_DEV_ARCHIVE = MP_DEV_KB / "archive"


def ensure_mp_dev_dirs() -> None:
    MP_DEV_EXPORT.mkdir(parents=True, exist_ok=True)
    MP_DEV_ARCHIVE.mkdir(parents=True, exist_ok=True)
