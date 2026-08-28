"""Bootstrap: chat-watch daemon (pythonw + venv)."""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / ".venv" / "Lib" / "site-packages"
if SITE.is_dir() and str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from autostart_util import append_autostart_log
    from env_loader import load_env
    from subprocess_win import kill_processes_matching

    load_env()
    append_autostart_log("bootstrap_ninjasin_watch starting")
    try:
        kill_processes_matching("bootstrap_ninjasin_watch.py", exclude_pid=os.getpid())
        kill_processes_matching("watchdog.py", exclude_pid=os.getpid())
        runpy.run_module("watchdog", run_name="__main__")
    except Exception as exc:
        append_autostart_log(f"bootstrap_ninjasin_watch FAILED: {exc!r}")
        raise


if __name__ == "__main__":
    main()
