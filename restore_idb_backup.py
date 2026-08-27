"""Restore mp.weixin.qq.com IndexedDB from reset backup (learning / R2 experiment).

用法（先完全退出微信）:
  python restore_idb_backup.py
  python restore_idb_backup.py --dry-run
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from mp_capture.idb_reader import DEFAULT_PROFILES, IDB_NAMES

DEFAULT_BACKUP = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore WeChat mp IndexedDB from backup")
    parser.add_argument("--backup", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.backup.is_dir():
        print(f"[ERR] backup not found: {args.backup}")
        sys.exit(1)

    profiles = DEFAULT_PROFILES
    dest: Path | None = None
    for multitab in profiles.glob("multitab_*/IndexedDB"):
        candidate = multitab / IDB_NAMES[0]
        dest = candidate
        break
    if dest is None:
        print("[ERR] live IndexedDB path not found")
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if dest.is_dir():
        live_backup = (
            Path(r"F:\ext\knowledge-base\wechat\mp-scroll\restore-backup") / stamp / dest.name
        )
        print(f"[plan] move live -> {live_backup}")
        if not args.dry_run:
            live_backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dest), str(live_backup))

    print(f"[plan] restore {args.backup} -> {dest}")
    if args.dry_run:
        return
    shutil.copytree(args.backup, dest)
    total = sum(f.stat().st_size for f in dest.iterdir() if f.is_file())
    print(f"[ok] restored ({total} bytes). Restart WeChat -> subscription -> scroll test.")


if __name__ == "__main__":
    main()
