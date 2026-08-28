"""Ensure mp_capture does not import root-level export scripts."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDB_REGISTRY = ROOT / "mp_capture" / "idb_registry.py"


def test_idb_registry_uses_wxlocal_shared():
    source = IDB_REGISTRY.read_text(encoding="utf-8")
    assert "from export_mp_dev" not in source
    assert "from ninjasin_dedup" not in source
    assert "from mp_dev_filter" not in source
    assert "wxlocal.shared" in source
