"""Login autostart entry: wait for KB/data paths, spawn both daemon bootstraps."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autostart_util import append_autostart_log, resolve_pythonw, wait_for_paths
from subprocess_win import CREATE_NO_WINDOW


def _spawn_bootstrap(pyw: Path, script: str) -> int | None:
    target = ROOT / script
    if not target.is_file():
        append_autostart_log(f"ERROR missing {target}")
        return None
    err_log = ROOT / "output" / f"autostart_{script.replace('.py', '')}.log"
    err_log.parent.mkdir(parents=True, exist_ok=True)
    log_fh = err_log.open("a", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(
        [str(pyw), str(target)],
        cwd=str(ROOT),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
        env=env,
    )
    append_autostart_log(f"spawned {script} pid={proc.pid} log={err_log.name}")
    return proc.pid


def main() -> int:
    append_autostart_log("bootstrap_autostart begin")
    if not wait_for_paths():
        return 1
    pyw = resolve_pythonw(ROOT)
    if pyw.name != "pythonw.exe" and not pyw.is_file():
        append_autostart_log(f"ERROR pythonw missing: {pyw}")
        return 1
    append_autostart_log(f"using pythonw={pyw}")
    pids = []
    for script in ("bootstrap_mp_watch.py", "bootstrap_ninjasin_watch.py"):
        pid = _spawn_bootstrap(pyw, script)
        if pid:
            pids.append(pid)
        time.sleep(1)
    if len(pids) < 2:
        append_autostart_log(f"ERROR only spawned {len(pids)}/2 bootstraps")
        return 1
    append_autostart_log(f"bootstrap_autostart done pids={pids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
