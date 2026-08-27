"""Windows 无窗口 subprocess 辅助。"""
from __future__ import annotations

import subprocess
import sys

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def run_silent(*popenargs, **kwargs):
    """subprocess.run，Windows 下不弹出控制台。"""
    if sys.platform == "win32":
        flags = kwargs.get("creationflags", 0)
        kwargs["creationflags"] = flags | CREATE_NO_WINDOW
    return subprocess.run(*popenargs, **kwargs)


def kill_processes_matching(substring: str, *, exclude_pid: int | None = None) -> None:
    """按命令行子串结束进程（Windows，无窗口）。"""
    if sys.platform != "win32" or not substring:
        return
    exclude = exclude_pid or 0
    ps = (
        "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.CommandLine -like '*{substring}*' -and $_.ProcessId -ne {exclude} }} | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    run_silent(
        ["powershell", "-WindowStyle", "Hidden", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
