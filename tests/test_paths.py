"""Smoke tests for paths.ensure_decrypted_dir (no WeChat / no network)."""
from __future__ import annotations

import pytest


@pytest.fixture
def paths_module(monkeypatch, tmp_path):
    import wxlocal.config.paths as paths

    out = tmp_path / "output"
    canonical = out / "decrypted"
    legacy = tmp_path / "decrypted"
    monkeypatch.setattr(paths, "OUTPUT_DIR", out)
    monkeypatch.setattr(paths, "DECRYPTED_DIR", canonical)
    monkeypatch.setattr(paths, "LEGACY_DECRYPTED_DIR", legacy)
    return paths


def test_ensure_decrypted_dir_migrates_legacy(paths_module):
    paths = paths_module
    (paths.LEGACY_DECRYPTED_DIR / "message").mkdir(parents=True)
    (paths.LEGACY_DECRYPTED_DIR / "message" / "test.db").write_text("x", encoding="utf-8")

    result = paths.ensure_decrypted_dir()

    assert result == paths.DECRYPTED_DIR
    assert (paths.DECRYPTED_DIR / "message" / "test.db").is_file()
    assert not paths.LEGACY_DECRYPTED_DIR.exists()


def test_ensure_decrypted_dir_prefers_canonical(paths_module):
    paths = paths_module
    (paths.DECRYPTED_DIR / "message").mkdir(parents=True)
    (paths.LEGACY_DECRYPTED_DIR / "message").mkdir(parents=True)

    result = paths.ensure_decrypted_dir()

    assert result == paths.DECRYPTED_DIR
    assert paths.LEGACY_DECRYPTED_DIR.is_dir()


def test_ensure_decrypted_dir_creates_empty(paths_module):
    paths = paths_module

    result = paths.ensure_decrypted_dir()

    assert result == paths.DECRYPTED_DIR
    assert paths.DECRYPTED_DIR.is_dir()
