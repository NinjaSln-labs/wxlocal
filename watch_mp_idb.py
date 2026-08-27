"""后台监控：滑列表 → 累积 URL → 自动抓标题 → 开发向导出。

用法:
  python watch_mp_idb.py                 # 默认每 45s 跑完整 pipeline
  python watch_mp_idb.py --once          # 跑一轮
  python watch_mp_idb.py --no-enrich     # 只扫 IDB，不 HTTP 抓标题
  python watch_mp_idb.py --interval 30
"""
from __future__ import annotations

import argparse
import atexit
import logging
import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from mp_capture.idb_registry import run_pipeline
from paths import MP_SCROLL_ERROR_LOG, MP_SCROLL_STATE_DIR, MP_SCROLL_WATCH_LOG, OUTPUT_DIR, ensure_mp_scroll_dirs

STATE_DIR = MP_SCROLL_STATE_DIR
LOG_FILE = OUTPUT_DIR / "mp_idb_watch.log"
PID_FILE = STATE_DIR / "mp_idb_watch.pid"
DEFAULT_INTERVAL = int(os.environ.get("MP_SCROLL_INTERVAL", "15"))
DEFAULT_OCR_EVERY = int(os.environ.get("MP_SCROLL_OCR_EVERY", "8"))  # 约 2 分钟 OCR 一次

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
    ensure_mp_scroll_dirs()
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

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ensure_mp_scroll_dirs()

    logger = logging.getLogger("watch_mp_idb")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        for path in (LOG_FILE, MP_SCROLL_WATCH_LOG):
            try:
                fh = logging.FileHandler(path, encoding="utf-8", delay=True)
                fh.setFormatter(fmt)
                logger.addHandler(fh)
            except OSError:
                pass
        try:
            eh = logging.FileHandler(MP_SCROLL_ERROR_LOG, encoding="utf-8", delay=True)
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


def run_once(logger: logging.Logger, *, enrich: bool, ocr: bool) -> None:
    result = run_pipeline(enrich=enrich, ocr=ocr)
    scan = result["scan"]
    enrich_stats = result["enrich"]
    body_stats = result.get("body_enrich", {})
    export_stats = result["export"]
    logger.info(
        "scan live=%s (full=%s triple=%s) total=%s new=%s ocr=%s ocr_new=%s",
        scan.get("live_count"),
        scan.get("full_count"),
        scan.get("triple_count"),
        scan["total"],
        len(scan["new_urls"]),
        scan.get("ocr_titles", 0),
        scan.get("ocr_new", 0),
    )
    if scan.get("ocr_error"):
        logger.warning("ocr: %s", scan["ocr_error"])
    for url in scan["new_urls"][:5]:
        logger.info("  + %s", url[:100])
    if enrich_stats.get("skipped"):
        logger.warning("enrich skipped (proxy %s not reachable?)", os.environ.get("WECHAT_FETCH_PROXY", "6696"))
    elif enrich_stats.get("fetched"):
        logger.info(
            "enrich fetched=%s titles=%s failed=%s",
            enrich_stats["fetched"],
            enrich_stats["titles"],
            enrich_stats["failed"],
        )
    if body_stats.get("fetched"):
        logger.info(
            "body enrich fetched=%s bodies=%s failed=%s",
            body_stats["fetched"],
            body_stats["bodies"],
            body_stats["failed"],
        )
    logger.info("export dev_kept=%s -> %s", export_stats["dev_kept"], export_stats["export_json"])


def main() -> None:
    logger = setup_logging()
    _install_excepthook(logger)

    parser = argparse.ArgumentParser(description="滑列表全自动 pipeline")
    parser.add_argument("--once", action="store_true", help="跑一轮后退出")
    parser.add_argument("--no-enrich", action="store_true", help="不 HTTP 抓标题")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="IDB 扫描间隔（秒，默认 15）")
    parser.add_argument("--ocr-every", type=int, default=DEFAULT_OCR_EVERY, help="每 N 轮 IDB 扫描才 OCR 一次（默认 8≈2min）")
    parser.add_argument("--no-ocr", action="store_true", help="完全关闭 OCR")
    args = parser.parse_args()

    if not args.once and not acquire_pid_lock():
        logger.info("already running (pid file: %s)", PID_FILE)
        return

    enrich = not args.no_enrich
    ocr_enabled = not args.no_ocr and os.environ.get("MP_SCROLL_OCR", "0") not in (
        "0",
        "false",
        "False",
    )
    tick = 0
    if args.once:
        run_once(logger, enrich=enrich, ocr=ocr_enabled)
        return

    logger.info(
        "mp-scroll pipeline started pid=%s interval=%ss enrich=%s ocr=%s ocr_every=%s log=%s",
        os.getpid(),
        args.interval,
        enrich,
        ocr_enabled,
        args.ocr_every,
        LOG_FILE,
    )
    while True:
        try:
            tick += 1
            do_ocr = ocr_enabled and (tick % max(1, args.ocr_every) == 0)
            run_once(logger, enrich=enrich, ocr=do_ocr)
        except Exception as exc:
            logger.exception("pipeline failed: %s", exc)
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if _LOGGER is not None:
            _LOGGER.exception("watch_mp_idb fatal exit")
        raise
