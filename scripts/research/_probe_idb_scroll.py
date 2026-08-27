"""Probe IDB for new content beyond URL count."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from mp_capture.idb_reader import extract_titles, extract_urls, find_idb_dirs, read_idb_bytes
from mp_capture.idb_registry import load_registry
from mp_capture.parsers import normalize_article_url

ROOT = Path(__file__).resolve().parent


def read_one_idb(idb_dir) -> bytes:
    from mp_capture.idb_reader import read_idb_bytes

    return read_idb_bytes([idb_dir])


def main() -> None:
    registry = load_registry()
    reg_urls = set(registry.get("items", {}).keys())

    print("=== per-store ===")
    all_live: set[str] = set()
    for idb in find_idb_dirs():
        blob = read_one_idb(idb)
        urls = extract_urls(blob)
        titles = extract_titles(blob)
        newest = max(idb.iterdir(), key=lambda f: f.stat().st_mtime)
        ts = datetime.fromtimestamp(newest.stat().st_mtime)
        norm = {normalize_article_url(u) for u in urls if normalize_article_url(u)}
        new_vs_reg = norm - reg_urls
        all_live |= norm
        print(f"{idb.parent.name}/{idb.name}")
        print(f"  mtime={ts} size={newest.stat().st_size} blob={len(blob)}")
        print(f"  urls={len(norm)} titles={len(titles)} new_vs_registry={len(new_vs_reg)}")
        for u in list(new_vs_reg)[:5]:
            print(f"    + {u[:100]}")
        for t in titles[:8]:
            print(f"    title: {t[:70]}")

    print("\n=== combined live vs registry ===")
    print(f"live={len(all_live)} registry={len(reg_urls)}")
    print(f"live-new={len(all_live - reg_urls)} registry-not-in-live={len(reg_urls - all_live)}")

    # broader URL patterns in xworker
    xworker = next((d for d in find_idb_dirs() if "xworker" in d.name), None)
    if xworker:
        blob = read_one_idb(xworker)
        text = blob.decode("utf-8", errors="replace")
        patterns = [
            r"https?://mp\.weixin\.qq\.com/[^\s\"'\\<>]{5,200}",
            r"https?://[^\s\"'\\<>]*weixin[^\s\"'\\<>]{5,200}",
        ]
        print("\n=== xworker broad patterns ===")
        for pat in patterns:
            hits = re.findall(pat, text)
            uniq = sorted(set(hits))
            print(f"  {pat[:40]}... hits={len(hits)} unique={len(uniq)}")
            for h in uniq[:5]:
                print(f"    {h[:90]}")

        # chinese title-like strings near dev keywords
        print("\n=== xworker chinese snippets (dev-ish) ===")
        for m in re.finditer(r"[\u4e00-\u9fff]{6,40}", text):
            s = m.group(0)
            if any(k in s for k in ("AI", "开源", "模型", "Agent", "代码", "GitHub", "Claude", "Skill", "RAG")):
                print(f"  {s}")

    # recently updated last_seen in registry
    items = sorted(registry["items"].values(), key=lambda x: x.get("last_seen", ""), reverse=True)
    print("\n=== registry last_seen top 5 ===")
    for it in items[:5]:
        print(f"  seen={it.get('seen_count')} {it.get('last_seen')} {it.get('title') or it['url'][:60]}")


if __name__ == "__main__":
    main()
