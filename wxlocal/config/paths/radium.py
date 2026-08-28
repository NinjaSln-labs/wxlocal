"""WeChat Chromium profile root."""
from __future__ import annotations

import os
from pathlib import Path


def default_radium_profiles() -> Path:
    """Resolve radium web profiles dir (WeChat 4.x).

    Prefer an existing directory. Current installs often use Roaming; older
    docs / machines may use LocalAppData.
    """
    override = os.environ.get("WECHAT_RADIUM_PROFILES", "").strip()
    if override:
        return Path(override)

    home = Path.home()
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "") or str(home / "AppData" / "Roaming")
    candidates = [
        Path(roaming) / "Tencent" / "xwechat" / "radium" / "web" / "profiles",
        Path(local) / "Tencent" / "xwechat" / "radium" / "web" / "profiles" if local else None,
        home / "AppData" / "Roaming" / "Tencent" / "xwechat" / "radium" / "web" / "profiles",
        home / "AppData" / "Local" / "Tencent" / "xwechat" / "radium" / "web" / "profiles",
    ]
    for path in candidates:
        if path is not None and path.is_dir():
            return path
    # Fallback for error messages / first-run mkdir probes
    return candidates[0]
