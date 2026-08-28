"""Smoke tests for R4 console_scripts entry points (import only, no WeChat)."""
from __future__ import annotations


def test_config_shims_match_package():
    import config as root_config
    import paths as root_paths
    from wxlocal.config import config as pkg_config
    from wxlocal.config import paths as pkg_paths

    assert root_config.DATA_ROOT == pkg_config.DATA_ROOT
    assert root_paths.ROOT == pkg_paths.ROOT


def test_pipeline_daemon_main_callable():
    from wxlocal.pipelines.chat_watch.daemon import main as watch_main
    from wxlocal.pipelines.mp_scroll.daemon import main as scroll_main

    assert callable(watch_main)
    assert callable(scroll_main)


def test_export_and_web_main_callable():
    from wxlocal.export.cli import main as export_main
    from wxlocal.web.app import main as web_main

    assert callable(export_main)
    assert callable(web_main)


def test_root_shims_delegate():
    import app
    import main
    import watchdog
    import watch_mp_idb

    assert callable(watchdog.main)
    assert callable(watch_mp_idb.main)
    assert callable(app.main)
    assert callable(main.main)
