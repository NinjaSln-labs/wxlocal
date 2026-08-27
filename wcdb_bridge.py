"""进程内调用 wcdb-key-tool，避免 python.exe 子进程弹窗。"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType

WCDB_TOOL = Path(__file__).resolve().parent / "vendor" / "wcdb-key-tool-main" / "wcdb_key_tool_windows.py"
_WCDB: ModuleType | None = None


def _load_wcdb() -> ModuleType:
    global _WCDB
    if _WCDB is not None:
        return _WCDB
    if not WCDB_TOOL.is_file():
        raise FileNotFoundError(f"wcdb tool missing: {WCDB_TOOL}")
    spec = importlib.util.spec_from_file_location("wcdb_key_tool_windows", WCDB_TOOL)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load wcdb tool: {WCDB_TOOL}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    _WCDB = mod
    return mod


def run_extract(db_storage: Path, keys_file: Path, logger: logging.Logger) -> bool:
    wcdb = _load_wcdb()
    args = argparse.Namespace(db_dir=str(db_storage), output=str(keys_file), decrypt=False)
    try:
        wcdb.cmd_extract(args)
    except SystemExit as exc:
        if exc.code:
            logger.error("wcdb extract exit code=%s", exc.code)
            return False
    except Exception as exc:
        logger.exception("wcdb extract failed: %s", exc)
        return False
    return keys_file.is_file()


def run_decrypt(db_storage: Path, decrypted_dir: Path, keys_file: Path, logger: logging.Logger) -> bool:
    wcdb = _load_wcdb()
    try:
        wcdb.decrypt_all(str(db_storage), str(decrypted_dir), str(keys_file))
    except SystemExit as exc:
        if exc.code:
            logger.error("wcdb decrypt exit code=%s", exc.code)
            return False
    except Exception as exc:
        logger.exception("wcdb decrypt failed: %s", exc)
        return False
    return True
