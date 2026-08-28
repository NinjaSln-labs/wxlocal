"""Background monitor: scroll feed → accumulate URLs → enrich → dev export.

Usage:
  wxlocal-mp-scroll                 # default ~45s pipeline loop
  wxlocal-mp-scroll --once          # one round
  wxlocal-mp-scroll --no-enrich
  wxlocal-mp-scroll --interval 30
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from mp_capture.idb_registry import run_pipeline

from wxlocal.config.paths import (
    LEGACY_MP_SCROLL_PID,
    LEGACY_MP_SCROLL_WATCH_LOG,
    MP_SCROLL_ERROR_LOG,
    MP_SCROLL_PID,
    MP_SCROLL_WATCH_LOG,
    OUTPUT_DIR,
    ensure_mp_scroll_dirs,
)
from wxlocal.shared.daemon import acquire_pid_lock, install_excepthook, setup_daemon_logging

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STATE_DIR = MP_SCROLL_PID.parent
LOG_FILE = OUTPUT_DIR / "mp_scroll.log"
PID_FILE = MP_SCROLL_PID
LEGACY_PID_FILES = (LEGACY_MP_SCROLL_PID,)
DEFAULT_INTERVAL = int(os.environ.get("MP_SCROLL_INTERVAL", "15"))
DEFAULT_OCR_EVERY = int(os.environ.get("MP_SCROLL_OCR_EVERY", "8"))


def setup_logging() -> logging.Logger:
    log_targets = (LOG_FILE, MP_SCROLL_WATCH_LOG, LEGACY_MP_SCROLL_WATCH_LOG)
    return setup_daemon_logging(
        "watch_mp_idb",
        log_targets,
        error_log=MP_SCROLL_ERROR_LOG,
        prepare=lambda: (OUTPUT_DIR.mkdir(parents=True, exist_ok=True), ensure_mp_scroll_dirs()),
    )


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
    parser = argparse.ArgumentParser(description="滑列表全自动 pipeline")
    parser.add_argument("--once", action="store_true", help="跑一轮后退出")
    parser.add_argument("--no-enrich", action="store_true", help="不 HTTP 抓标题")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="IDB 扫描间隔（秒，默认 15）")
    parser.add_argument("--ocr-every", type=int, default=DEFAULT_OCR_EVERY, help="每 N 轮 IDB 扫描才 OCR 一次（默认 8≈2min）")
    parser.add_argument("--no-ocr", action="store_true", help="完全关闭 OCR")
    args = parser.parse_args()

    logger = setup_logging()
    install_excepthook(logger)

    if not args.once and not acquire_pid_lock(
        PID_FILE, legacy_pid_files=LEGACY_PID_FILES, prepare=ensure_mp_scroll_dirs
    ):
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
        logging.getLogger("watch_mp_idb").exception("watch_mp_idb fatal exit")
        raise
