"""Daemon status and stop for mp-scroll and chat-watch (used by status_*.bat)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wxlocal.shared.daemon import pid_running
from paths import MP_SCROLL_STATE_DIR, NINJASIN_STATE_DIR, OUTPUT_DIR

_PIPELINES = {
    "mp-scroll": {
        "label": "mp-scroll (IndexedDB watch)",
        "patterns": ("bootstrap_mp_watch", "watch_mp_idb.py"),
        "pid_file": MP_SCROLL_STATE_DIR / "mp_idb_watch.pid",
        "process_pattern": "watch_mp_idb.py",
    },
    "chat-watch": {
        "label": "chat-watch (contact export)",
        "patterns": ("bootstrap_ninjasin_watch", "watchdog.py"),
        "pid_file": NINJASIN_STATE_DIR / "ninjasin_watch.pid",
        "process_pattern": "watchdog.py",
    },
}

_LEGACY_PID_FILES = (
    Path(os.environ.get("LOCALAPPDATA", "")) / "wxlocal" / "mp_idb_watch.pid",
    Path(os.environ.get("LOCALAPPDATA", "")) / "wechat-reader" / "mp_idb_watch.pid",
)


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


def stop_pipelines(only: str = "all") -> None:
    from subprocess_win import kill_processes_matching

    names = list(_PIPELINES) if only in ("all", "") else [only]
    for name in names:
        cfg = _PIPELINES.get(name)
        if not cfg:
            continue
        for pattern in cfg["patterns"]:
            kill_processes_matching(pattern)
        pid_file = cfg["pid_file"]
        if pid_file.is_file():
            pid_file.unlink(missing_ok=True)
    if only in ("all", "", "mp-scroll"):
        for legacy in _LEGACY_PID_FILES:
            if legacy.is_file():
                legacy.unlink(missing_ok=True)


def show_status(only: str = "all") -> None:
    if only in ("all", "mp-scroll"):
        cfg = _PIPELINES["mp-scroll"]
        _format_daemon(cfg["label"], cfg["pid_file"], cfg["process_pattern"])
    if only in ("all", "chat-watch"):
        cfg = _PIPELINES["chat-watch"]
        _format_daemon(cfg["label"], cfg["pid_file"], cfg["process_pattern"])
    print(f"repo: {ROOT}")
    print(f"logs: {OUTPUT_DIR}")


def main() -> int:
    cmd = "status"
    only = "all"
    if len(sys.argv) >= 2:
        if sys.argv[1] in ("stop", "status"):
            cmd = sys.argv[1]
            only = sys.argv[2] if len(sys.argv) > 2 else "all"
        else:
            only = sys.argv[1]

    if cmd == "stop":
        if only not in ("all", "mp-scroll", "chat-watch"):
            print(f"unknown pipeline: {only}", file=sys.stderr)
            return 1
        stop_pipelines(only)
        print(f"[ok] stop attempted ({only})")
        return 0

    if only not in ("all", "mp-scroll", "chat-watch"):
        print(f"unknown pipeline: {only}", file=sys.stderr)
        return 1
    show_status(only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
