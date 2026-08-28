"""R8: export/archive live in package; root files are shims."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_chat_watch_export_and_archive_importable():
    from wxlocal.pipelines.chat_watch.archive import main as archive_main
    from wxlocal.pipelines.chat_watch.export import export_contact, main as export_main

    assert callable(export_contact)
    assert callable(export_main)
    assert callable(archive_main)


def test_export_package_modules_importable():
    from wxlocal.export import messages, mp_capture_export, mp_dev, mp_idb, mp_registry

    assert callable(messages.main)
    assert callable(mp_dev.main)
    assert callable(mp_idb.main)
    assert callable(mp_capture_export.main)
    assert callable(mp_registry.main)


def test_daemon_no_root_archive_import():
    text = (ROOT / "wxlocal" / "pipelines" / "chat_watch" / "daemon.py").read_text(encoding="utf-8")
    assert "from archive_ninjasin_delta" not in text
    assert "from export_contact" not in text
    assert "wxlocal.pipelines.chat_watch.export" in text
    assert "wxlocal.pipelines.chat_watch.archive" in text
    assert "bootstrap_legacy_imports" not in text


def test_ops_scripts_exist():
    ops = ROOT / "scripts" / "ops"
    for name in (
        "enrich_bodies_batch.py",
        "rescan_titles.py",
        "reset_mp_scroll.py",
        "restore_idb_backup.py",
        "mp_capture_status.py",
        "run_mp_capture.py",
    ):
        assert (ops / name).is_file(), name
