"""Login autostart helpers: path wait, pythonw resolve, launch logging."""
from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path

from wxlocal.config._root import PROJECT_ROOT

ROOT = PROJECT_ROOT
AUTOSTART_LOG = ROOT / "output" / "autostart_launch.log"


def append_autostart_log(msg: str) -> None:
    tag = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    line = f"{tag} [bootstrap] {msg}"
    try:
        AUTOSTART_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUTOSTART_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def _drive_ready(path: Path) -> bool:
    drive = path.drive
    if not drive:
        return True
    return Path(f"{drive}\\").exists()


def wait_for_paths(*, max_wait: int = 120, poll: float = 2.0) -> bool:
    """Wait until WECHAT_KB_ROOT / WECHAT_DATA_ROOT drives and dirs are usable."""
    from wxlocal.config.env_loader import load_env

    load_env()

    kb_raw = os.environ.get("WECHAT_KB_ROOT", "").strip()
    data_raw = os.environ.get("WECHAT_DATA_ROOT", "").strip()
    kb_path = Path(kb_raw) if kb_raw else ROOT / "data" / "knowledge-base"
    data_path = Path(data_raw) if data_raw else None

    deadline = time.time() + max_wait
    while time.time() < deadline:
        ready = True
        if not _drive_ready(kb_path):
            ready = False
        elif not kb_path.is_dir():
            try:
                kb_path.mkdir(parents=True, exist_ok=True)
            except OSError:
                ready = False
        if data_path is not None:
            if not _drive_ready(data_path):
                ready = False
            elif not data_path.is_dir():
                ready = False
        if ready:
            try:
                (ROOT / "output").mkdir(parents=True, exist_ok=True)
            except OSError:
                ready = False
        if ready:
            append_autostart_log(
                f"paths ready kb={kb_path} data={data_path or '(auto)'}"
            )
            return True
        append_autostart_log(
            f"waiting for paths kb={kb_path} data={data_path or '(auto)'} ..."
        )
        time.sleep(poll)

    append_autostart_log(f"ERROR paths not ready after {max_wait}s")
    return False


def resolve_pythonw(project_root: Path | None = None) -> Path:
    """Prefer WXLOCAL_PYTHON from .env, then venv pythonw."""
    from wxlocal.config.env_loader import load_env

    load_env()
    root = project_root or ROOT
    for key in ("WXLOCAL_PYTHON", "WECHAT_READER_PYTHON"):
        candidate = os.environ.get(key, "").strip()
        if candidate:
            path = Path(candidate)
            if path.is_file():
                return path
    venv_pyw = root / ".venv" / "Scripts" / "pythonw.exe"
    if venv_pyw.is_file():
        return venv_pyw
    return Path("pythonw.exe")
