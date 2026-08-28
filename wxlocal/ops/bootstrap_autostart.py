"""Login autostart entry: wait for KB/data paths, spawn both daemon bootstraps."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from wxlocal.config._root import PROJECT_ROOT
from wxlocal.core.subprocess_win import CREATE_NO_WINDOW
from wxlocal.ops.autostart import append_autostart_log, resolve_pythonw, wait_for_paths

ROOT = PROJECT_ROOT
_BOOTSTRAP_MODULES = (
    "wxlocal.pipelines.mp_scroll.bootstrap",
    "wxlocal.pipelines.chat_watch.bootstrap",
)


def _spawn_bootstrap(pyw: Path, module: str) -> int | None:
    tag = module.replace("wxlocal.pipelines.", "").replace(".", "_")
    err_log = ROOT / "output" / f"autostart_{tag}.log"
    err_log.parent.mkdir(parents=True, exist_ok=True)
    log_fh = err_log.open("a", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(
        [str(pyw), "-m", module],
        cwd=str(ROOT),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
        env=env,
    )
    append_autostart_log(f"spawned -m {module} pid={proc.pid} log={err_log.name}")
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
    for module in _BOOTSTRAP_MODULES:
        pid = _spawn_bootstrap(pyw, module)
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
