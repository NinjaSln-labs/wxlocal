"""Smoke tests for daemon_util pid lock helpers."""
from __future__ import annotations

from pathlib import Path

from daemon_util import acquire_pid_lock, pid_running, release_pid_lock


def test_pid_running_current_process():
    import os

    assert pid_running(os.getpid()) is True
    assert pid_running(0) is False
    assert pid_running(-1) is False


def test_acquire_pid_lock_blocks_second_holder(tmp_path: Path):
    pid_file = tmp_path / "daemon.pid"
    assert acquire_pid_lock(pid_file) is True
    assert pid_file.read_text(encoding="utf-8").strip() != ""
    assert acquire_pid_lock(pid_file) is False
    release_pid_lock(pid_file)
    assert not pid_file.exists()
