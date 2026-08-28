"""Step 3a: compare LevelDB same-value pairing vs blob scan."""
from __future__ import annotations

import json
import sys

from wxlocal.pipelines.mp_scroll.capture.idb_blink import extract_triple_cards_from_storage
from wxlocal.pipelines.mp_scroll.capture.idb_leveldb import extract_triple_cards_from_leveldb_dirs
from wxlocal.pipelines.mp_scroll.capture.idb_reader import article_key, find_storage_dirs, triple_to_url, url_has_sn

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    dirs = find_storage_dirs()
    blob_cards = extract_triple_cards_from_storage(dirs)
    ldb_cards = extract_triple_cards_from_leveldb_dirs(dirs)

    blob_titled = {c["triple"] for c in blob_cards if c.get("title")}
    ldb_titled = {c["triple"] for c in ldb_cards if c.get("title")}
    only_ldb = ldb_titled - blob_titled
    only_blob = blob_titled - ldb_titled

    print("=== extractors ===")
    print(f"blob scan:    {len(blob_cards)} triples, {len(blob_titled)} with title")
    print(f"leveldb:      {len(ldb_cards)} triples, {len(ldb_titled)} with title")
    print(f"ldb-only titles: {len(only_ldb)}  blob-only titles: {len(only_blob)}")

    reg = json.load(open(r"F:\ext\knowledge-base\wechat\mp-capture\registry\idb_registry.json", encoding="utf-8"))
    awaiting = {r["article_key"] for r in reg["items"].values() if r.get("status") == "awaiting_sn"}
    ldb_map = {
        article_key(triple_to_url(c["triple"])): c.get("title", "")
        for c in ldb_cards
        if c.get("title")
    }
    recover = [k for k in awaiting if k in ldb_map]
    print(f"\nawaiting_sn={len(awaiting)} recoverable via leveldb={len(recover)}")
    for k in recover[:8]:
        print(f"  {ldb_map[k][:55]}")

    merged = {c["triple"]: c for c in blob_cards}
    for c in ldb_cards:
        prev = merged.get(c["triple"])
        if prev is None:
            merged[c["triple"]] = c
        elif c.get("title") and not prev.get("title"):
            prev["title"] = c["title"]
    print(f"\nmerged unique triples with title: {sum(1 for c in merged.values() if c.get('title'))}/{len(merged)}")


if __name__ == "__main__":
    main()
