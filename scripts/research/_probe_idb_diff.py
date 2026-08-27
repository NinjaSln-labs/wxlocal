"""Compare live IndexedDB vs saved exports."""
from __future__ import annotations

import json
import re
from pathlib import Path

from export_mp_idb import IDB_DIRS, extract_urls, read_idb_bytes
from mp_capture.parsers import normalize_article_url


def norm_set(urls: list[str]) -> set[str]:
    return {u for u in (normalize_article_url(x) for x in urls) if u}


def load_export(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "all_urls" in data:
        return norm_set(data["all_urls"])
    if "items" in data and isinstance(data["items"], list):
        return norm_set([x.get("url", "") for x in data["items"]])
    return set()


def main() -> None:
    blob = read_idb_bytes()
    live = norm_set(extract_urls(blob))
    latest = load_export(Path(r"F:\ext\knowledge-base\wechat\mp-capture\exports\mp_idb_latest.json"))
    old = load_export(Path(r"F:\ext\knowledge-base\wechat\mp-capture\exports\idb_articles.json"))

    text = blob.decode("utf-8", errors="replace")
    raw_urls = re.findall(r"https?://mp\.weixin\.qq\.com/s[^\s\"'\\<>]{10,400}", text)

    print("=== IDB dirs ===")
    for d in IDB_DIRS:
        if not d.is_dir():
            print(f"  MISSING {d}")
            continue
        files = list(d.iterdir())
        total = sum(f.stat().st_size for f in files if f.is_file())
        newest = max((f for f in files if f.is_file()), key=lambda f: f.stat().st_mtime, default=None)
        mtime = newest.stat().st_mtime if newest else 0
        from datetime import datetime

        ts = datetime.fromtimestamp(mtime).isoformat(sep=" ", timespec="seconds") if mtime else "-"
        print(f"  {d.name}: {len(files)} files, {total} bytes, newest={newest.name if newest else '-'} @ {ts}")

    print("\n=== URL counts (normalized) ===")
    print(f"  live now:      {len(live)}")
    print(f"  mp_idb_latest: {len(latest)}")
    print(f"  idb_articles:  {len(old)} (first probe)")
    print(f"  raw occurrences in blob: {len(raw_urls)} (unique raw: {len(set(raw_urls))})")

    new_vs_latest = live - latest
    new_vs_old = live - old
    gone_vs_old = old - live

    print("\n=== Diff ===")
    print(f"  new since 13:11 export: {len(new_vs_latest)}")
    print(f"  new since first probe:  {len(new_vs_old)}")
    print(f"  gone since first probe: {len(gone_vs_old)}")

    if new_vs_latest:
        print("\n  NEW urls (since latest export):")
        for u in sorted(new_vs_latest)[:20]:
            print(f"    + {u}")

    if gone_vs_old:
        print("\n  REMOVED urls (since first probe):")
        for u in sorted(gone_vs_old)[:10]:
            print(f"    - {u}")


if __name__ == "__main__":
    main()
