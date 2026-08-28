"""Bootstrap: chat-watch daemon (pythonw + venv)."""
from __future__ import annotations

import os
import sys

from wxlocal.config._root import PROJECT_ROOT

SITE = PROJECT_ROOT / ".venv" / "Lib" / "site-packages"
if SITE.is_dir() and str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    from wxlocal.config.env_loader import load_env
    from wxlocal.core.subprocess_win import kill_processes_matching
    from wxlocal.ops.autostart import append_autostart_log
    from wxlocal.pipelines.chat_watch.daemon import main as daemon_main

    load_env()
    append_autostart_log("bootstrap_chat_watch starting")
    try:
        kill_processes_matching("chat_watch.bootstrap", exclude_pid=os.getpid())
        kill_processes_matching("bootstrap_chat_watch.py", exclude_pid=os.getpid())
        kill_processes_matching("bootstrap_ninjasin_watch.py", exclude_pid=os.getpid())
        kill_processes_matching("watchdog.py", exclude_pid=os.getpid())
        kill_processes_matching("chat_watch.daemon", exclude_pid=os.getpid())
        kill_processes_matching("wxlocal-watch", exclude_pid=os.getpid())
        daemon_main()
    except Exception as exc:
        append_autostart_log(f"bootstrap_chat_watch FAILED: {exc!r}")
        raise


if __name__ == "__main__":
    main()
