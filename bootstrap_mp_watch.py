"""Bootstrap: base pythonw + venv site-packages, single process."""
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

from env_loader import load_env

load_env()

from subprocess_win import kill_processes_matching

kill_processes_matching("bootstrap_mp_watch.py", exclude_pid=os.getpid())
kill_processes_matching("watch_mp_idb.py", exclude_pid=os.getpid())

runpy.run_module("watch_mp_idb", run_name="__main__")
