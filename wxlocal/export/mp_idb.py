"""从微信 IndexedDB 导出滑列表缓存的文章 → 开发向语料。

只滑订阅号列表即可；数据在 WeChatAppEx 的 IndexedDB 里，不走 mitm HTTP。

用法:
  python export_mp_idb.py
  python export_mp_idb.py --fetch-titles
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from wxlocal.shared.http_fetch import fetch_http_body
from mp_capture.idb_reader import extract_titles, read_storage_bytes, scan_live
from wxlocal.shared.mp_filter import is_dev_related
from wxlocal.config.paths import MP_CAPTURE_ARCHIVE, MP_CAPTURE_EXPORT, MP_CAPTURE_KB, ensure_mp_capture_dirs

PROXY = os.environ.get("WECHAT_FETCH_PROXY", "http://127.0.0.1:6696")
UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "MicroMessenger/8.0.49"
)


def fetch_title_from_page(url: str, opener: urllib.request.OpenerDirector) -> tuple[str, str]:
    import re

    body = ""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": UA, "Referer": "https://mp.weixin.qq.com/"},
        )
        with opener.open(req, timeout=30) as resp:
            page = resp.read().decode("utf-8", errors="replace")
        og = re.search(r'property="og:title"\s+content="([^"]+)"', page, re.I)
        if og:
            title = og.group(1).strip()
            if title.endswith("-微信公众平台"):
                title = title[: -len("-微信公众平台")].strip()
            body = fetch_http_body(url) or ""
            return title, body
    except Exception:
        pass
    body = fetch_http_body(url)
    return "", body


def main() -> None:
    parser = argparse.ArgumentParser(description="从 IndexedDB 导出滑列表文章")
    parser.add_argument("--fetch-titles", action="store_true", help="HTTP 抓标题/正文")
    parser.add_argument("--all", action="store_true", help="不过滤开发向")
    args = parser.parse_args()

    ensure_mp_capture_dirs()
    cards, blob_size = scan_live()
    urls = [c["url"] for c in cards]
    blob = read_storage_bytes()
    orphan_titles = extract_titles(blob)

    items = [{"url": u, "title": "", "summary": "", "source_name": "", "source": "idb"} for u in urls]

    if args.fetch_titles:
        handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
        opener = urllib.request.build_opener(handler)
        print(f"抓取标题 {len(items)} 条 (proxy={PROXY})...")
        for i, it in enumerate(items, 1):
            title, body = fetch_title_from_page(it["url"], opener)
            if title:
                it["title"] = title
            if body:
                it["body"] = body
                it["body_source"] = "HTTP抓取"
            if i % 10 == 0:
                print(f"  ... {i}/{len(items)}")
            time.sleep(0.4)

    kept, dropped = [], []
    for it in items:
        ok, reason = (True, "all") if args.all else is_dev_related(
            it.get("title", ""), it.get("summary", ""), it.get("source_name", "")
        )
        it["filter_reason"] = reason
        if ok:
            kept.append(it)
        else:
            dropped.append(it)

    meta = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "source": "wechat IndexedDB (list scroll)",
        "idb_bytes": blob_size,
        "urls_found": len(urls),
        "orphan_titles_in_idb": len(orphan_titles),
        "kept": len(kept),
        "dropped": len(dropped),
        "filter": "all" if args.all else "mp_dev_filter.py",
    }

    stamp = datetime.now().strftime("%Y-%m-%d")
    batch = MP_CAPTURE_ARCHIVE / f"{stamp}-idb"
    batch.mkdir(parents=True, exist_ok=True)
    payload = {"meta": meta, "items": kept, "dropped_sample": dropped[:40], "all_urls": urls}
    out_json = batch / "mp_idb.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = MP_CAPTURE_EXPORT / "mp_idb_latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    (MP_CAPTURE_KB / "INDEX.md").write_text(
        "\n".join(
            [
                "# 公众号 · 抓包/列表语料",
                "",
                f"- IndexedDB 导出: `{meta['exported_at']}`",
                f"- 滑列表 URL: **{meta['urls_found']}** / 开发向 **{meta['kept']}**",
                f"- 注册表: [`registry/idb_registry.json`](../registry/idb_registry.json)",
                f"- mitm: [`exports/mp_capture_latest.json`](exports/mp_capture_latest.json)",
                f"- idb: [`exports/mp_idb_latest.json`](exports/mp_idb_latest.json)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"urls={len(urls)} kept={len(kept)} dropped={len(dropped)}")
    print(f"JSON: {out_json}")
    for it in kept[:12]:
        print(f"  - {it.get('title','')[:60] or it['url'][:60]}")


if __name__ == "__main__":
    main()
