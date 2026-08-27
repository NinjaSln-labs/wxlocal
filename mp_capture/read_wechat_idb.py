"""从微信 IndexedDB (mp.weixin.qq.com) 提取订阅号列表缓存（CLI 调试工具）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mp_capture.idb_reader import scan_live
from paths import MP_CAPTURE_EXPORT, ensure_mp_capture_dirs

OUT = MP_CAPTURE_EXPORT / "idb_articles.json"


def main() -> None:
    ensure_mp_capture_dirs()
    cards = scan_live()
    payload = {
        "meta": {"count": len(cards), "source": "read_wechat_idb.py"},
        "items": cards,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(cards)} items -> {OUT}")


if __name__ == "__main__":
    main()
