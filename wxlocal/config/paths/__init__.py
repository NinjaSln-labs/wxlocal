"""Knowledge-base and runtime paths (package entry — re-exports submodules)."""
from __future__ import annotations

from wxlocal.config.env_loader import load_env

# Must load .env before submodule imports read os.environ.
load_env()

from wxlocal.config.paths.chat_watch import (  # noqa: E402
    ARCHIVE_ROOT,
    CHAT_WATCH_KB,
    CHAT_WATCH_PID,
    CURATED_DIR,
    EXPORTS_DIR,
    LEGACY_CHAT_WATCH_PID,
    NINJASIN_CONTACT,
    NINJASIN_DAEMON_LOG,
    NINJASIN_ERROR_LOG,
    NINJASIN_KB,
    NINJASIN_LAUNCH_LOG,
    NINJASIN_STATE_DIR,
    WATCH_CONTACT,
    WENJIN_NINJASIN_KB,
    ensure_kb_dirs,
)
from wxlocal.config.paths.kb import KB_ROOT, ROOT, WECHAT_KB  # noqa: E402
from wxlocal.config.paths.mp_capture import (  # noqa: E402
    MP_CAPTURE_ARCHIVE,
    MP_CAPTURE_EXPORT,
    MP_CAPTURE_KB,
    MP_CAPTURE_RAW,
    MP_CAPTURE_REGISTRY,
    ensure_mp_capture_dirs,
)
from wxlocal.config.paths.mp_dev import MP_DEV_ARCHIVE, MP_DEV_EXPORT, MP_DEV_KB, ensure_mp_dev_dirs  # noqa: E402
from wxlocal.config.paths.mp_scroll import (  # noqa: E402
    LEGACY_MP_SCROLL_ERROR_LOG,
    LEGACY_MP_SCROLL_PID,
    LEGACY_MP_SCROLL_WATCH_LOG,
    MP_SCROLL_ARCHIVE,
    MP_SCROLL_ERROR_LOG,
    MP_SCROLL_EXPORT,
    MP_SCROLL_KB,
    MP_SCROLL_LAUNCH_LOG,
    MP_SCROLL_OCR_DIR,
    MP_SCROLL_PID,
    MP_SCROLL_STATE_DIR,
    MP_SCROLL_WATCH_LOG,
    ensure_mp_scroll_dirs,
)
from wxlocal.config.paths.radium import default_radium_profiles  # noqa: E402
from wxlocal.config.paths.runtime import (  # noqa: E402
    DECRYPTED_DIR,
    LEGACY_DECRYPTED_DIR,
    OUTPUT_DIR,
    ensure_decrypted_dir,
    ensure_output_dirs,
)
