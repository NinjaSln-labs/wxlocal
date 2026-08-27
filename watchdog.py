"""后台守护进程：检测微信登录后自动提取密钥、解密、导出指定联系人聊天记录。

用法:
  python watchdog.py              # 前台运行
  python watchdog.py --once       # 单次同步后退出
  python watchdog.py --interval 60  # 自定义轮询间隔（秒）
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from config import DATA_ROOT, OUTPUT_DIR, find_user_db_storage
from daemon_util import acquire_pid_lock, install_excepthook, setup_daemon_logging
from export_contact import export_contact
from paths import (
    WATCH_CONTACT,
    NINJASIN_DAEMON_LOG,
    NINJASIN_ERROR_LOG,
    NINJASIN_STATE_DIR,
    OUTPUT_DIR as OUTPUT_ROOT,
    ensure_decrypted_dir,
    ensure_kb_dirs,
)
from scan_keys_v41 import find_weixin_pid
from wcdb_bridge import run_decrypt, run_extract

PROJECT_ROOT = Path(__file__).resolve().parent
KEYS_FILE = OUTPUT_ROOT / "all_keys.json"
LOG_FILE = OUTPUT_ROOT / "daemon.log"
WCDB_TOOL = PROJECT_ROOT / "vendor" / "wcdb-key-tool-main" / "wcdb_key_tool_windows.py"
DELTA_SCRIPT = PROJECT_ROOT / "archive_ninjasin_delta.py"
PID_FILE = NINJASIN_STATE_DIR / "ninjasin_watch.pid"

DEFAULT_INTERVAL = int(os.environ.get("WECHAT_WATCH_INTERVAL", "60"))
WECHAT_WAIT_INTERVAL = 15


def setup_logging() -> logging.Logger:
    return setup_daemon_logging(
        "watchdog",
        (LOG_FILE, NINJASIN_DAEMON_LOG),
        error_log=NINJASIN_ERROR_LOG,
        prepare=lambda: (os.makedirs(OUTPUT_DIR, exist_ok=True), ensure_kb_dirs()),
    )


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
    decrypted_dir = ensure_decrypted_dir()
    if not run_decrypt(db_storage, decrypted_dir, KEYS_FILE, logger):
        return False
    logger.info("解密完成 -> %s", decrypted_dir)
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
    install_excepthook(logger)

    if not args.once and not acquire_pid_lock(PID_FILE, prepare=ensure_kb_dirs):
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
        logging.getLogger("watchdog").exception("watchdog fatal exit")
        raise
