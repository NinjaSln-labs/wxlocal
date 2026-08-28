"""Smoke tests for config.find_user_db_storage."""
from __future__ import annotations

from wxlocal.config.config import find_user_db_storage


def test_find_user_db_storage_skips_system_dirs(tmp_path):
    (tmp_path / "all_users").mkdir()
    (tmp_path / "Backup").mkdir()
    user = tmp_path / "user_a"
    (user / "db_storage").mkdir(parents=True)
    (user / "db_storage" / "message").mkdir()

    found = find_user_db_storage(tmp_path)

    assert found == user / "db_storage"


def test_find_user_db_storage_missing_root(tmp_path):
    assert find_user_db_storage(tmp_path / "missing") is None
