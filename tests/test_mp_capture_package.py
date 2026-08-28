"""R9/R10: capture package under wxlocal.pipelines.mp_scroll.capture."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_capture_package_importable():
    from wxlocal.pipelines.mp_scroll.capture.idb_registry import run_pipeline
    from wxlocal.pipelines.mp_scroll.capture.run import main as run_main

    assert callable(run_pipeline)
    assert callable(run_main)


def test_mp_scroll_daemon_uses_package_capture():
    text = (ROOT / "wxlocal" / "pipelines" / "mp_scroll" / "daemon.py").read_text(encoding="utf-8")
    assert "from mp_capture.idb_registry" not in text
    assert "wxlocal.pipelines.mp_scroll.capture.idb_registry" in text


def test_root_mp_capture_package_removed():
    assert not (ROOT / "mp_capture" / "idb_registry.py").is_file()
