"""Regression: .env / environ must be visible when path constants bind."""
from __future__ import annotations

import os


def test_watch_contact_not_stuck_on_default():
    """Fresh import path is covered by other tests; assert runtime binding used env."""
    from wxlocal.config.paths import WATCH_CONTACT

    env_val = os.environ.get("WECHAT_WATCH_CONTACT", "").strip()
    if env_val:
        assert WATCH_CONTACT == env_val
    else:
        # No env set in this process — default is acceptable
        assert WATCH_CONTACT == "FileTransfer"


def test_load_env_before_paths_import_order():
    """config.paths.__init__ must call load_env before submodule imports."""
    from pathlib import Path

    init_src = (Path(__file__).resolve().parents[1] / "wxlocal" / "config" / "paths" / "__init__.py").read_text(
        encoding="utf-8"
    )
    load_pos = init_src.find("load_env()")
    chat_import = init_src.find("from wxlocal.config.paths.chat_watch import")
    assert load_pos != -1
    assert chat_import != -1
    assert load_pos < chat_import
