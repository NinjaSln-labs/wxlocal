"""Deep probe: all WeChat radium storage + mitm + registry."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from mp_capture.idb_reader import (
    extract_cards,
    extract_titles,
    extract_urls,
    find_storage_dirs,
    read_storage_bytes,
)
from mp_capture.idb_registry import load_registry, proxy_ready

PROFILES = __import__("paths").default_radium_profiles()
MP_URL = re.compile(r"https?://mp\.weixin\.qq\.com/s[^\s\"'\\<>]{10,400}")
CN = re.compile(r"[\u4e00-\u9fff]{6,50}")


def probe_store(path: Path) -> dict:
    blob = read_storage_bytes([path])
    text = blob.decode("utf-8", errors="replace")
    newest = max((f for f in path.iterdir() if f.is_file()), key=lambda f: f.stat().st_mtime)
    return {
        "path": f"{path.parent.name}/{path.name}",
        "mtime": datetime.fromtimestamp(newest.stat().st_mtime).isoformat(sep=" ", timespec="seconds"),
        "blob": len(blob),
        "urls": len(extract_urls(blob)),
        "titles": len(extract_titles(blob)),
        "cards": len(extract_cards(blob)),
        "mp_urls_raw": len(set(MP_URL.findall(text))),
        "cn_snippets": len(CN.findall(text)),
    }


def main() -> None:
    print("=== storage stores ===")
    for d in find_storage_dirs(PROFILES):
        info = probe_store(d)
        print(json.dumps(info, ensure_ascii=False))

    # extra IDB not in find_storage_dirs
    print("\n=== extra indexeddb ===")
    for idb in sorted(PROFILES.glob("multitab_*/IndexedDB/*.leveldb")):
        if idb.name.startswith(("https_mp", "weixin_xworker")):
            continue
        info = probe_store(idb)
        print(json.dumps(info, ensure_ascii=False))
        blob = read_storage_bytes([idb])
        text = blob.decode("utf-8", errors="replace")
        for t in CN.findall(text)[:8]:
            if any(k in t for k in ("AI", "开源", "模型", "Agent", "GitHub", "Claude", "Skill", "评测", "Eval")):
                print("  snippet:", t)

    print("\n=== session storage ===")
    for ss in sorted(PROFILES.glob("multitab_*/Session Storage")):
        blob = read_storage_bytes([ss])
        text = blob.decode("utf-8", errors="replace")
        urls = set(MP_URL.findall(text))
        print(f"{ss.parent.name}/Session Storage blob={len(blob)} mp_urls={len(urls)}")
        for u in list(urls)[:3]:
            print(" ", u[:90])

    registry = load_registry()
    items = list(registry["items"].values())
    print("\n=== registry ===")
    print(f"total={len(items)} with_title={sum(1 for x in items if x.get('title'))}")
    print(f"proxy_ready={proxy_ready()}")

    # mitm store
    cap = Path(r"F:\ext\knowledge-base\wechat\mp-capture\exports\mp_capture_latest.json")
    if cap.is_file():
        data = json.loads(cap.read_text(encoding="utf-8"))
        print("\n=== mitm capture ===")
        print(f"items={len(data.get('items', []))} flows_seen={data.get('flows_seen')}")
        for it in data.get("items", [])[:5]:
            print(" ", (it.get("title") or it.get("url") or "")[:80])


if __name__ == "__main__":
    main()
