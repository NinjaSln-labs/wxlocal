"""Shared helpers for wxlocal background daemons."""
from __future__ import annotations

import atexit
import logging
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

_LOGGERS: dict[str, logging.Logger] = {}


def pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def migrate_pid_file(canonical: Path, *legacy: Path) -> None:
    """Prefer canonical pid file; rename legacy file if present."""
    if canonical.is_file():
        return
    for old in legacy:
        if not old.is_file():
            continue
        try:
            import shutil

            shutil.move(str(old), str(canonical))
        except OSError:
            try:
                canonical.parent.mkdir(parents=True, exist_ok=True)
                canonical.write_text(old.read_text(encoding="utf-8"), encoding="utf-8")
                old.unlink(missing_ok=True)
            except OSError:
                pass
        break


def acquire_pid_lock(
    pid_file: Path,
    *,
    legacy_pid_files: Sequence[Path] = (),
    prepare: Callable[[], None] | None = None,
) -> bool:
    if prepare is not None:
        prepare()
    migrate_pid_file(pid_file, *legacy_pid_files)
    if pid_file.is_file():
        try:
            old_pid = int(pid_file.read_text(encoding="utf-8").strip())
        except ValueError:
            old_pid = 0
        if pid_running(old_pid):
            return False
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(release_pid_lock, pid_file)
    for old in legacy_pid_files:
        if old.is_file() and old != pid_file:
            old.unlink(missing_ok=True)
    return True


def release_pid_lock(pid_file: Path) -> None:
    if not pid_file.is_file():
        return
    try:
        if int(pid_file.read_text(encoding="utf-8").strip()) == os.getpid():
            pid_file.unlink(missing_ok=True)
    except (ValueError, OSError):
        pass


def setup_daemon_logging(
    logger_name: str,
    log_files: Sequence[Path],
    *,
    error_log: Path | None = None,
    prepare: Callable[[], None] | None = None,
) -> logging.Logger:
    cached = _LOGGERS.get(logger_name)
    if cached is not None:
        return cached

    if prepare is not None:
        prepare()

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        for path in log_files:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                fh = logging.FileHandler(path, encoding="utf-8", delay=True)
                fh.setFormatter(fmt)
                logger.addHandler(fh)
            except OSError:
                pass
        if error_log is not None:
            try:
                error_log.parent.mkdir(parents=True, exist_ok=True)
                eh = logging.FileHandler(error_log, encoding="utf-8", delay=True)
                eh.setLevel(logging.ERROR)
                eh.setFormatter(fmt)
                logger.addHandler(eh)
            except OSError:
                pass
        if sys.stdout is not None and getattr(sys.stdout, "write", None):
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(fmt)
            logger.addHandler(sh)
    _LOGGERS[logger_name] = logger
    return logger


def install_excepthook(logger: logging.Logger) -> None:
    def _hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        logger.critical("uncaught exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _hook
