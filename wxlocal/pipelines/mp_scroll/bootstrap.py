"""Bootstrap: mp-scroll daemon (pythonw + venv)."""
from __future__ import annotations

import os
import sys

from wxlocal._legacy import bootstrap_legacy_imports
from wxlocal.config._root import PROJECT_ROOT

SITE = PROJECT_ROOT / ".venv" / "Lib" / "site-packages"
if SITE.is_dir() and str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

bootstrap_legacy_imports()


def main() -> None:
    from autostart_util import append_autostart_log
    from env_loader import load_env

    from wxlocal.core.subprocess_win import kill_processes_matching
    from wxlocal.pipelines.mp_scroll.daemon import main as daemon_main

    load_env()
    append_autostart_log("bootstrap_mp_scroll starting")
    try:
        kill_processes_matching("bootstrap_mp_scroll.py", exclude_pid=os.getpid())
        kill_processes_matching("bootstrap_mp_watch.py", exclude_pid=os.getpid())
        kill_processes_matching("watch_mp_idb.py", exclude_pid=os.getpid())
        kill_processes_matching("mp_scroll.daemon", exclude_pid=os.getpid())
        kill_processes_matching("wxlocal-mp-scroll", exclude_pid=os.getpid())
        daemon_main()
    except Exception as exc:
        append_autostart_log(f"bootstrap_mp_scroll FAILED: {exc!r}")
        raise


if __name__ == "__main__":
    main()
