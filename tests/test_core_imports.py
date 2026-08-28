"""Core package import contracts (R7+)."""
from __future__ import annotations


def test_core_modules_importable():
    from wxlocal.core import decrypt, key_parser, keys, messages, subprocess_win, wcdb

    assert callable(keys.find_weixin_pid)
    assert callable(keys.copy_and_decrypt)
    assert callable(decrypt.decrypt_with_fallback)
    assert callable(messages.read_messages)
    assert callable(key_parser.parse_key_input)
    assert callable(wcdb.run_extract)
    assert callable(subprocess_win.kill_processes_matching)


def test_package_consumers_use_wxlocal_core():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    samples = [
        root / "wxlocal" / "web" / "service.py",
        root / "wxlocal" / "export" / "cli.py",
        root / "wxlocal" / "pipelines" / "chat_watch" / "daemon.py",
    ]
    for path in samples:
        text = path.read_text(encoding="utf-8")
        assert "from wxlocal.core" in text, path.name
        assert "from decrypt_db import" not in text, path.name
        assert "from scan_keys_v41 import" not in text, path.name
        assert "from wcdb_bridge import" not in text, path.name
