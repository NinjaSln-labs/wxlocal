"""Smoke tests for wxlocal.ops.autostart (no WeChat / no network)."""
from __future__ import annotations

from pathlib import Path

from wxlocal.ops import autostart as autostart_util


def test_resolve_pythonw_prefers_env_over_venv(monkeypatch, tmp_path):
    custom = tmp_path / "custom_pythonw.exe"
    custom.write_text("", encoding="utf-8")
    monkeypatch.setattr("wxlocal.config.env_loader.load_env", lambda *a, **k: None)
    monkeypatch.setenv("WXLOCAL_PYTHON", str(custom))
    assert autostart_util.resolve_pythonw(tmp_path) == custom


def test_resolve_pythonw_falls_back_to_venv(monkeypatch, tmp_path):
    venv_pyw = tmp_path / ".venv" / "Scripts" / "pythonw.exe"
    venv_pyw.parent.mkdir(parents=True)
    venv_pyw.write_text("", encoding="utf-8")
    monkeypatch.setattr("wxlocal.config.env_loader.load_env", lambda *a, **k: None)
    monkeypatch.delenv("WXLOCAL_PYTHON", raising=False)
    monkeypatch.delenv("WECHAT_READER_PYTHON", raising=False)
    assert autostart_util.resolve_pythonw(tmp_path) == venv_pyw


def test_wait_for_paths_succeeds_with_local_kb(monkeypatch, tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    out = tmp_path / "output"
    monkeypatch.setenv("WECHAT_KB_ROOT", str(kb))
    monkeypatch.setenv("WECHAT_DATA_ROOT", str(tmp_path / "wechat_data"))
    (tmp_path / "wechat_data").mkdir()
    monkeypatch.setattr(autostart_util, "ROOT", tmp_path)
    monkeypatch.setattr(autostart_util, "AUTOSTART_LOG", out / "autostart_launch.log")
    assert autostart_util.wait_for_paths(max_wait=5, poll=0.1) is True
    assert out.is_dir()
