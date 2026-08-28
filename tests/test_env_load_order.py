"""Env must bind into path/config constants in a fresh process (R5 regression).

Import-time constants break if load_env() runs after os.environ is read.
Same-process reloads are unreliable — probe with a subprocess + temp .env.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _run_fresh_paths_probe(env_file: Path) -> dict[str, str]:
    """Import wxlocal.config.paths in a clean process that only sees env_file."""
    probe = textwrap.dedent(
        """
        import json
        import os
        from pathlib import Path

        for key in (
            "WECHAT_WATCH_CONTACT",
            "WECHAT_KB_ROOT",
            "WECHAT_DATA_ROOT",
            "WECHAT_RADIUM_PROFILES",
        ):
            os.environ.pop(key, None)

        # Real import path: paths/__init__ must load_env before binding constants.
        from wxlocal.config import paths
        from wxlocal.config import config as cfg

        print(json.dumps({
            "WATCH_CONTACT": paths.WATCH_CONTACT,
            "KB_ROOT": str(paths.KB_ROOT),
            "DATA_ROOT": cfg.DATA_ROOT,
        }))
        """
    )
    env = dict(os.environ)
    env["WXLOCAL_ENV_FILE"] = str(env_file)
    for key in (
        "WECHAT_WATCH_CONTACT",
        "WECHAT_KB_ROOT",
        "WECHAT_DATA_ROOT",
        "WECHAT_RADIUM_PROFILES",
    ):
        env.pop(key, None)

    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, f"probe failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_temp_env_binds_watch_contact_and_kb(tmp_path: Path):
    env_file = tmp_path / ".env"
    kb = tmp_path / "kb-root"
    env_file.write_text(
        "\n".join(
            [
                "WECHAT_WATCH_CONTACT=ProbeContactR5",
                f"WECHAT_KB_ROOT={kb.as_posix()}",
                "WECHAT_DATA_ROOT=D:/probe/xwechat_files",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bound = _run_fresh_paths_probe(env_file)
    assert bound["WATCH_CONTACT"] == "ProbeContactR5", bound
    assert Path(bound["KB_ROOT"]) == kb, bound
    assert bound["DATA_ROOT"].replace("\\", "/") == "D:/probe/xwechat_files", bound


def test_load_env_before_paths_import_order():
    init_src = (REPO / "wxlocal" / "config" / "paths" / "__init__.py").read_text(encoding="utf-8")
    load_pos = init_src.find("load_env()")
    chat_import = init_src.find("from wxlocal.config.paths.chat_watch import")
    assert load_pos != -1 and chat_import != -1
    assert load_pos < chat_import


def test_config_loads_env_before_paths_import():
    src = (REPO / "wxlocal" / "config" / "config.py").read_text(encoding="utf-8")
    load_pos = src.find("load_env()")
    paths_import = src.find("from wxlocal.config.paths import")
    assert load_pos != -1 and paths_import != -1
    assert load_pos < paths_import
