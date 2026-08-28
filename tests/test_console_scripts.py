"""Smoke tests for console_scripts / package entry points (import only, no WeChat)."""
from __future__ import annotations


def test_config_package_exports():
    from pathlib import Path

    from wxlocal.config import config as pkg_config
    from wxlocal.config import paths as pkg_paths

    # DATA_ROOT comes from WECHAT_DATA_ROOT; empty is valid in CI without .env
    assert isinstance(pkg_config.DATA_ROOT, str)
    assert callable(pkg_config.find_user_db_storage)
    assert isinstance(pkg_paths.ROOT, Path)
    assert pkg_paths.ROOT.is_dir()


def test_pipeline_daemon_main_callable():
    from wxlocal.pipelines.chat_watch.daemon import main as watch_main
    from wxlocal.pipelines.mp_scroll.daemon import main as scroll_main

    assert callable(watch_main)
    assert callable(scroll_main)


def test_pipeline_bootstrap_main_callable():
    from wxlocal.ops.bootstrap_autostart import main as auto_boot
    from wxlocal.pipelines.chat_watch.bootstrap import main as chat_boot
    from wxlocal.pipelines.mp_scroll.bootstrap import main as scroll_boot

    assert callable(chat_boot)
    assert callable(scroll_boot)
    assert callable(auto_boot)


def test_export_and_web_main_callable():
    from wxlocal.export.cli import main as export_main
    from wxlocal.web.app import main as web_main

    assert callable(export_main)
    assert callable(web_main)
