"""Trace dev export provenance + locate recommendation scroll data."""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from mp_capture.idb_reader import (
    TRIPLEKEY_RE,
    article_key,
    extract_cards,
    find_storage_dirs,
    read_storage_bytes,
    url_has_sn,
)

ROOT = Path(__file__).resolve().parent
DEV = Path(r"F:\ext\knowledge-base\wechat\mp-scroll\exports\mp_scroll_dev_latest.json")
REG = Path(r"F:\ext\knowledge-base\wechat\mp-capture\registry\idb_registry.json")
BAK = Path(r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\registry\idb_registry.json")
BIZ = ROOT / "decrypted/message/biz_message_0.db"
PROFILES = __import__("paths").default_radium_profiles()
BACKUP_IDB = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def classify_full_provenance(row: dict) -> str:
    fs = (row.get("first_seen") or "")[:16]
    if fs <= "2026-08-27T13:25":
        return "A_idb_historical_pre_watch"
    if fs.startswith("2026-08-27T14:41"):
        return "B_idb_full_added_during_session"
    if fs.startswith("2026-08-27T15:14"):
        return "C_post_reset_server_reimport"
    return f"D_other_{fs}"


def extract_biz_urls() -> set[str]:
    if not BIZ.is_file():
        return set()
    conn = sqlite3.connect(BIZ)
    cur = conn.cursor()
    tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    urls: set[str] = set()
    url_re = re.compile(r"https?://mp\.weixin\.qq\.com/s\?[^\s\"<>\\]+")
    for table in tables:
        try:
            cols = [c[1] for c in cur.execute(f"PRAGMA table_info({table})")]
        except sqlite3.Error:
            continue
        for col in cols:
            if col.lower() not in (
                "buffer",
                "bytes",
                "msg",
                "content",
                "compresscontent",
                "xml",
                "messagecontent",
            ):
                continue
            try:
                rows = cur.execute(f"SELECT {col} FROM {table} LIMIT 2000").fetchall()
            except sqlite3.Error:
                continue
            for (raw,) in rows:
                if raw is None:
                    continue
                if isinstance(raw, memoryview):
                    raw = bytes(raw)
                text = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else str(raw)
                for m in url_re.finditer(text):
                    urls.add(m.group(0).replace("&amp;", "&"))
    conn.close()
    return urls


def scan_profiles() -> list[tuple]:
    pat_url = re.compile(rb"https?://mp\.weixin\.qq\.com/s\?__biz=[^\x00-\x1f\x7f]{10,200}")
    results = []
    for f in PROFILES.rglob("*"):
        if not f.is_file() or f.name == "LOCK":
            continue
        if f.suffix not in (".ldb", ".log") and f.name not in ("LOG", "LOG.old"):
            continue
        try:
            data = f.read_bytes()
        except OSError:
            continue
        nu = len(pat_url.findall(data))
        nt = len(TRIPLEKEY_RE.findall(data))
        if nu or nt:
            results.append(
                (
                    str(f.relative_to(PROFILES)),
                    len(data),
                    nu,
                    nt,
                    datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                )
            )
    results.sort(key=lambda x: -(x[2] + x[3]))
    return results


def main() -> None:
    dev = load_json(DEV)
    reg = load_json(REG)
    bak = load_json(BAK)
    reg_items = list(reg.get("items", {}).values())
    dev_items = dev.get("items", [])

    print("=" * 60)
    print("Q1: Where does dev_kept=135 come from?")
    print("=" * 60)
    print("dev export:", dev.get("meta", {}))

    reg_by_url = {v.get("url"): v for v in reg_items if v.get("url")}
    reg_by_key = {article_key(v["url"]): v for v in reg_items if v.get("url", "").startswith("http")}

    dev_buckets: Counter[str] = Counter()
    dev_examples: dict[str, list] = defaultdict(list)
    for it in dev_items:
        url = it.get("url", "")
        rk = reg_by_url.get(url)
        if not rk and url.startswith("ocr:"):
            rk = next((v for v in reg_items if v.get("url") == url), None)
        if not rk and it.get("article_key"):
            rk = reg_by_key.get(it["article_key"])
        if not rk:
            bucket = "unknown"
        elif rk.get("url_kind") == "ocr" or url.startswith("ocr:"):
            bucket = f"ocr_screen_capture|{rk.get('first_seen','')[:16]}"
        elif url_has_sn(url):
            bucket = classify_full_provenance(rk)
        else:
            bucket = f"triple_no_sn|{rk.get('first_seen','')[:16]}"
        dev_buckets[bucket] += 1
        if len(dev_examples[bucket]) < 2:
            dev_examples[bucket].append(it.get("title", "")[:55])

    for k, v in dev_buckets.most_common():
        print(f"  {v:3d}  {k}")
        for t in dev_examples[k]:
            print(f"       · {t}")

    # Pre-reset dev breakdown
    print("\n--- Pre-reset backup registry (before --all) ---")
    bak_items = list(bak.get("items", {}).values())
    bak_dev = [i for i in bak_items if i.get("dev_related")]
    bak_full_dev = [i for i in bak_dev if url_has_sn(i.get("url", ""))]
    bak_tri_dev = [
        i for i in bak_dev if i.get("url", "").startswith("http") and not url_has_sn(i.get("url", ""))
    ]
    bak_ocr_dev = [i for i in bak_dev if i.get("url_kind") == "ocr"]
    print(f"dev_related total: {len(bak_dev)} = full {len(bak_full_dev)} + triple {len(bak_tri_dev)} + ocr {len(bak_ocr_dev)}")

    bak_full = [i for i in bak_items if url_has_sn(i.get("url", ""))]
    c = Counter(classify_full_provenance(i) for i in bak_full)
    print("full URL provenance in backup:")
    for k, v in c.most_common():
        print(f"  {v:3d}  {k}")

    # biz_message overlap
    print("\n--- biz_message_0.db overlap ---")
    biz_urls = extract_biz_urls()
    full_reg = [i for i in reg_items if url_has_sn(i.get("url", ""))]
    reg_keys = {article_key(i["url"]) for i in full_reg}
    biz_keys = {article_key(u) for u in biz_urls}
    overlap = reg_keys & biz_keys
    print(f"biz_message unique URLs: {len(biz_urls)}")
    print(f"registry full URLs: {len(reg_keys)}")
    print(f"overlap (same biz|mid|idx): {len(overlap)}")
    print(f"full ONLY in registry (not in biz_message): {len(reg_keys - biz_keys)}")
    print(f"ONLY in biz_message (not in registry full): {len(biz_keys - reg_keys)}")

    print("\n" + "=" * 60)
    print("Q2: Where does recommendation scroll data go?")
    print("=" * 60)

    # triple timeline
    triple = [i for i in reg_items if i.get("url", "").startswith("http") and not url_has_sn(i["url"])]
    print(f"registry triple entries: {len(triple)}")
    for k, v in sorted(Counter(i.get("first_seen", "")[:16] for i in triple).items()):
        print(f"  first_seen {k}: {v}  status={Counter(i.get('status') for i in triple if i.get('first_seen','')[:16]==k)}")

    # backup idb vs live idb
    if BACKUP_IDB.is_dir():
        bak_blob = read_storage_bytes([BACKUP_IDB])
        bak_cards = extract_cards(bak_blob)
        bak_full = sum(1 for c in bak_cards if url_has_sn(c.get("url", "")))
        bak_tri = sum(1 for c in bak_cards if c.get("source_name") == "idb:triplekey")
        print(f"\nbackup IDB blob={len(bak_blob)} cards={len(bak_cards)} full={bak_full} triple={bak_tri}")

    print("\nLive storage dirs:")
    for d in find_storage_dirs():
        blob = read_storage_bytes([d])
        cards = extract_cards(blob)
        text = blob.decode("utf-8", "replace")
        print(
            f"  {d.parent.name}/{d.name}: blob={len(blob)} cards={len(cards)} "
            f"triplekey_raw={len(TRIPLEKEY_RE.findall(text))}"
        )

    print("\nAll profile files with mp URL or triplekey:")
    for rel, sz, nu, nt, mtime in scan_profiles()[:12]:
        print(f"  urls={nu} triple={nt} sz={sz} @{mtime}  {rel}")

    # scroll batch sample from backup registry
    scroll_tri = [i for i in triple if (i.get("first_seen") or "").startswith("2026-08-27T14:31")]
    print(f"\nScroll batch 14:31 triple sample ({len(scroll_tri)} total):")
    for i in scroll_tri[:3]:
        print(f"  {i.get('url','')[:85]}")
        print(f"    source_name={i.get('source_name')} status={i.get('status')} title={i.get('title')!r}")


if __name__ == "__main__":
    main()
