"""后台守护进程：检测微信登录后自动提取密钥、解密、导出指定联系人聊天记录。

用法:
  python watchdog.py              # 前台运行
  python watchdog.py --once       # 单次同步后退出
  python watchdog.py --interval 60  # 自定义轮询间隔（秒）
"""
from __future__ import annotations

import argparse
import atexit
import json
import logging
import os
import sys
import time
from pathlib import Path

from config import DATA_ROOT, OUTPUT_DIR
from export_contact import export_contact
from paths import (
    WATCH_CONTACT,
    NINJASIN_DAEMON_LOG,
    NINJASIN_ERROR_LOG,
    NINJASIN_STATE_DIR,
    ensure_kb_dirs,
)
from scan_keys_v41 import find_weixin_pid
from wcdb_bridge import run_decrypt, run_extract

PROJECT_ROOT = Path(__file__).resolve().parent
KEYS_FILE = PROJECT_ROOT / "output" / "all_keys.json"
DECRYPTED_DIR = PROJECT_ROOT / "decrypted"
LOG_FILE = PROJECT_ROOT / "output" / "daemon.log"
WCDB_TOOL = PROJECT_ROOT / "vendor" / "wcdb-key-tool-main" / "wcdb_key_tool_windows.py"
DELTA_SCRIPT = PROJECT_ROOT / "archive_ninjasin_delta.py"
PID_FILE = NINJASIN_STATE_DIR / "ninjasin_watch.pid"

DEFAULT_INTERVAL = 60
WECHAT_WAIT_INTERVAL = 15

_LOGGER: logging.Logger | None = None


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def acquire_pid_lock() -> bool:
    ensure_kb_dirs()
    if PID_FILE.is_file():
        try:
            old_pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        except ValueError:
            old_pid = 0
        if _pid_running(old_pid):
            return False
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(release_pid_lock)
    return True


def release_pid_lock() -> None:
    if not PID_FILE.is_file():
        return
    try:
        if int(PID_FILE.read_text(encoding="utf-8").strip()) == os.getpid():
            PID_FILE.unlink(missing_ok=True)
    except (ValueError, OSError):
        pass


def setup_logging() -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ensure_kb_dirs()

    logger = logging.getLogger("watchdog")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        for path in (LOG_FILE, NINJASIN_DAEMON_LOG):
            try:
                fh = logging.FileHandler(path, encoding="utf-8", delay=True)
                fh.setFormatter(fmt)
                logger.addHandler(fh)
            except OSError:
                pass
        try:
            eh = logging.FileHandler(NINJASIN_ERROR_LOG, encoding="utf-8", delay=True)
            eh.setLevel(logging.ERROR)
            eh.setFormatter(fmt)
            logger.addHandler(eh)
        except OSError:
            pass
        if sys.stdout is not None and getattr(sys.stdout, "write", None):
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(fmt)
            logger.addHandler(sh)
    _LOGGER = logger
    return logger


def _install_excepthook(logger: logging.Logger) -> None:
    def _hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        logger.critical("uncaught exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _hook


def find_user_db_storage(data_root: str) -> Path | None:
    root = Path(data_root)
    if not root.is_dir():
        return None
    for name in os.listdir(root):
        if name in ("all_users", "Backup"):
            continue
        db_storage = root / name / "db_storage"
        if db_storage.is_dir():
            return db_storage
    return None


def keys_file_valid(keys_path: Path, db_storage: Path) -> bool:
    """检查缓存密钥是否仍能解密 message_0.db。"""
    if not keys_path.is_file():
        return False
    try:
        keys = json.loads(keys_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not keys:
        return False

    msg_key = None
    for rel, info in keys.items():
        if "message_0.db" in rel.replace("/", "\\"):
            msg_key = info.get("enc_key")
            break
    if not msg_key:
        return False

    msg_db = db_storage / "message" / "message_0.db"
    if not msg_db.is_file():
        return False

    return bool(msg_key)


def run_wcdb_extract(db_storage: Path, logger: logging.Logger) -> bool:
    if not WCDB_TOOL.is_file():
        logger.error("未找到 wcdb-key-tool: %s", WCDB_TOOL)
        return False

    logger.info("开始提取密钥 (wcdb in-process)...")
    if not run_extract(db_storage, KEYS_FILE, logger):
        return False
    logger.info("密钥提取成功 -> %s", KEYS_FILE)
    return KEYS_FILE.is_file()


def run_wcdb_decrypt(logger: logging.Logger) -> bool:
    if not KEYS_FILE.is_file():
        logger.error("密钥文件不存在: %s", KEYS_FILE)
        return False

    db_storage = find_user_db_storage(DATA_ROOT)
    if not db_storage:
        logger.error("未找到 db_storage: %s", DATA_ROOT)
        return False

    logger.info("开始解密数据库 (wcdb in-process)...")
    if not run_decrypt(db_storage, DECRYPTED_DIR, KEYS_FILE, logger):
        return False
    logger.info("解密完成 -> %s", DECRYPTED_DIR)
    return True


def run_export_ninjasin(logger: logging.Logger) -> bool:
    logger.info("导出 %s 聊天记录...", WATCH_CONTACT)
    try:
        result = export_contact(WATCH_CONTACT)
    except Exception as exc:
        logger.exception("%s 导出失败: %s", WATCH_CONTACT, exc)
        return False
    logger.info(
        "%s 导出完成 -> %s 条",
        WATCH_CONTACT,
        result.get("message_count", 0),
    )
    return True


def run_ninjasin_delta_archive(logger: logging.Logger) -> bool:
    if not DELTA_SCRIPT.is_file():
        logger.warning("未找到增量归档脚本: %s", DELTA_SCRIPT)
        return False
    try:
        from archive_ninjasin_delta import main as archive_delta_main

        stats = archive_delta_main()
        logger.info(
            "chat-watch 增量归档: net_new=%s dups_skipped=%s parsed=%s",
            stats.get("net_new"),
            stats.get("dups"),
            stats.get("parsed"),
        )
        return True
    except SystemExit as exc:
        if exc.code:
            logger.error("chat-watch 增量归档退出 code=%s", exc.code)
            return False
        return True
    except Exception as exc:
        logger.exception("chat-watch 增量归档失败: %s", exc)
        return False


def get_db_mtime_marker(db_storage: Path) -> float:
    """取关键数据库的最大修改时间，用于检测新消息。"""
    markers = [
        db_storage / "message" / "message_0.db",
        db_storage / "message" / "message_0.db-wal",
        db_storage / "session" / "session.db",
        db_storage / "session" / "session.db-wal",
    ]
    latest = 0.0
    for p in markers:
        if p.is_file():
            latest = max(latest, p.stat().st_mtime)
    return latest


def sync_once(logger: logging.Logger, force_extract: bool = False) -> bool:
    db_storage = find_user_db_storage(DATA_ROOT)
    if not db_storage:
        logger.warning("未找到数据目录: %s", DATA_ROOT)
        return False

    pid = find_weixin_pid()
    if not pid:
        logger.info("微信未运行，跳过同步")
        return False

    logger.info("检测到微信进程 PID=%d", pid)

    need_extract = force_extract or not keys_file_valid(KEYS_FILE, db_storage)
    if need_extract:
        if not run_wcdb_extract(db_storage, logger):
            return False
    else:
        logger.info("使用缓存密钥 %s", KEYS_FILE)

    if not run_wcdb_decrypt(logger):
        return False
    if not run_export_ninjasin(logger):
        return False
    run_ninjasin_delta_archive(logger)
    return True


def main():
    parser = argparse.ArgumentParser(description="微信指定联系人聊天记录自动同步")
    parser.add_argument("--once", action="store_true", help="单次同步后退出")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="轮询间隔（秒）")
    parser.add_argument("--force-extract", action="store_true", help="强制重新提取密钥")
    args = parser.parse_args()

    logger = setup_logging()
    _install_excepthook(logger)

    if not args.once and not acquire_pid_lock():
        logger.info("ninjasin-watch already running (pid file: %s)", PID_FILE)
        return

    logger.info(
        "ninjasin-watch started pid=%s interval=%ds once=%s",
        os.getpid(),
        args.interval,
        args.once,
    )

    last_marker = 0.0
    wechat_was_running = False

    if args.once:
        ok = sync_once(logger, force_extract=args.force_extract)
        sys.exit(0 if ok else 1)

    while True:
        try:
            pid = find_weixin_pid()
            if pid:
                db_storage = find_user_db_storage(DATA_ROOT)
                marker = get_db_mtime_marker(db_storage) if db_storage else 0.0

                if not wechat_was_running:
                    logger.info("微信刚启动/刚检测到，执行首次同步...")
                    sync_once(logger, force_extract=args.force_extract)
                    last_marker = marker
                    wechat_was_running = True
                elif marker > last_marker:
                    logger.info(
                        "检测到数据库变更 (mtime %.0f -> %.0f)，重新同步...",
                        last_marker,
                        marker,
                    )
                    sync_once(logger, force_extract=False)
                    last_marker = marker

                time.sleep(args.interval)
            else:
                if wechat_was_running:
                    logger.info("微信已退出")
                wechat_was_running = False
                time.sleep(WECHAT_WAIT_INTERVAL)
        except Exception as exc:
            logger.exception("sync loop failed: %s", exc)
            time.sleep(WECHAT_WAIT_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if _LOGGER is not None:
            _LOGGER.exception("watchdog fatal exit")
        raise
