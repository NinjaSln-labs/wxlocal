"""Print daemon status for mp-scroll and chat-watch (used by status_*.bat)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from daemon_util import pid_running
from paths import MP_SCROLL_STATE_DIR, NINJASIN_STATE_DIR, OUTPUT_DIR


def _read_pid(pid_file: Path) -> int | None:
    if not pid_file.is_file():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _format_daemon(name: str, pid_file: Path, pattern: str) -> None:
    print(f"--- {name} ---")
    pid = _read_pid(pid_file)
    if pid is not None:
        running = pid_running(pid)
        state = "running" if running else "stale"
        print(f"pid file: {pid_file}")
        print(f"pid:      {pid} ({state})")
    else:
        print(f"pid file: not found ({pid_file})")

    try:
        import subprocess

        ps = (
            "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.CommandLine -like '*{pattern}*' }} | "
            "Select-Object ProcessId, @{N='Started';E={$_.CreationDate}} | "
            "Format-Table -AutoSize"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.stdout.strip():
            print(out.stdout.strip())
        elif out.returncode == 0:
            print("process: not running")
    except OSError as exc:
        print(f"process lookup failed: {exc}")
    print()


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    if only in ("all", "mp-scroll"):
        _format_daemon(
            "mp-scroll (IndexedDB watch)",
            MP_SCROLL_STATE_DIR / "mp_idb_watch.pid",
            "watch_mp_idb.py",
        )
    if only in ("all", "chat-watch"):
        _format_daemon(
            "chat-watch (contact export)",
            NINJASIN_STATE_DIR / "ninjasin_watch.pid",
            "watchdog.py",
        )
    print(f"repo: {ROOT}")
    print(f"logs: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
