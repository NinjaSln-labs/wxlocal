"""WeChat Chromium profile root."""
from __future__ import annotations

import os
from pathlib import Path


def default_radium_profiles() -> Path:
    override = os.environ.get("WECHAT_RADIUM_PROFILES", "").strip()
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        return Path(local) / "Tencent" / "xwechat" / "radium" / "web" / "profiles"
    return Path.home() / "AppData" / "Roaming" / "Tencent" / "xwechat" / "radium" / "web" / "profiles"
