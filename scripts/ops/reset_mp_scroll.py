"""重置滑列表 pipeline 缓存，便于重新测试。

用法:
  python reset_mp_scroll.py                  # 只清注册表（微信 IDB 保留）
  python reset_mp_scroll.py --wechat-idb     # 额外清微信 IndexedDB（需先关微信）
  python reset_mp_scroll.py --all            # 注册表 + 微信 IDB + OCR 截图
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from wxlocal.pipelines.mp_scroll.capture.idb_reader import DEFAULT_PROFILES, IDB_NAMES
from wxlocal.config.paths import (
    MP_CAPTURE_EXPORT,
    MP_CAPTURE_REGISTRY,
    MP_SCROLL_EXPORT,
    MP_SCROLL_OCR_DIR,
    ensure_mp_capture_dirs,
    ensure_mp_scroll_dirs,
)

BACKUP_ROOT = Path(r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup")


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup_file(path: Path, dest_dir: Path) -> None:
    if not path.is_file():
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest_dir / path.name)


def clear_registry(backup_dir: Path) -> None:
    ensure_mp_capture_dirs()
    backup_file(MP_CAPTURE_REGISTRY, backup_dir)
    backup_file(MP_CAPTURE_EXPORT / "idb_registry_latest.json", backup_dir)
    empty = {
        "meta": {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "last_scan_at": None,
            "last_live_count": 0,
            "total_urls": 0,
            "reset_at": datetime.now().isoformat(timespec="seconds"),
        },
        "items": {},
    }
    MP_CAPTURE_REGISTRY.write_text(json.dumps(empty, ensure_ascii=False, indent=2), encoding="utf-8")
    (MP_CAPTURE_EXPORT / "idb_registry_latest.json").write_text(
        json.dumps(empty, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[ok] registry cleared -> backup {backup_dir}")


def clear_scroll_export(backup_dir: Path) -> None:
    ensure_mp_scroll_dirs()
    latest = MP_SCROLL_EXPORT / "mp_scroll_dev_latest.json"
    backup_file(latest, backup_dir)
    if latest.is_file():
        latest.unlink()
    print("[ok] mp_scroll_dev_latest.json removed (will rebuild on next export)")


def clear_ocr_shots() -> None:
    ensure_mp_scroll_dirs()
    if MP_SCROLL_OCR_DIR.is_dir():
        for f in MP_SCROLL_OCR_DIR.glob("*"):
            if f.is_file():
                f.unlink(missing_ok=True)
    print("[ok] OCR temp cleared")


def clear_wechat_idb() -> bool:
    profiles = Path(os.environ.get("WECHAT_RADIUM_PROFILES", str(DEFAULT_PROFILES)))
    if not profiles.is_dir():
        print("[skip] WeChat profiles not found")
        return False

    # 微信运行时 leveldb 被锁，删了也不可靠
    for exe in ("Weixin.exe", "WeChatAppEx.exe"):
        try:
            import subprocess

            out = subprocess.check_output(
                ["tasklist", "/FI", f"IMAGENAME eq {exe}", "/FO", "CSV", "/NH"],
                text=True,
                errors="ignore",
            )
            if exe.lower() in out.lower() and "INFO:" not in out:
                print(f"[ERR] {exe} still running — close WeChat first, then rerun with --wechat-idb")
                return False
        except Exception:
            pass

    removed = 0
    backup_dir = BACKUP_ROOT / _stamp() / "wechat-idb"
    for multitab in profiles.glob("multitab_*/IndexedDB"):
        for name in IDB_NAMES:
            path = multitab / name
            if not path.is_dir():
                continue
            dest = backup_dir / path.parent.parent.name / path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(dest))
            removed += 1
            print(f"[ok] moved {path} -> {dest}")

    if removed == 0:
        print("[skip] no WeChat IDB dirs found")
    else:
        print(f"[ok] WeChat IDB cleared ({removed} stores), backup at {backup_dir}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset mp-scroll pipeline cache")
    parser.add_argument("--wechat-idb", action="store_true", help="Also clear WeChat native IndexedDB")
    parser.add_argument("--all", action="store_true", help="registry + wechat-idb + ocr shots + export latest")
    args = parser.parse_args()

    backup_dir = BACKUP_ROOT / _stamp() / "registry"
    clear_registry(backup_dir)
    if args.all:
        clear_scroll_export(backup_dir)
        clear_ocr_shots()
    if args.wechat_idb or args.all:
        if not clear_wechat_idb():
            sys.exit(1)

    print("\nNext:")
    print("  1. Open WeChat -> Subscription feed")
    print("  2. wscript //nologo run_mp_idb_watch.vbs")
    print("  3. Scroll and watch log for new=N")


if __name__ == "__main__":
    main()
