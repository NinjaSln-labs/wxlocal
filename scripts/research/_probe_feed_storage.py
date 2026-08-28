"""Probe all radium storage for feed titles and short URLs."""
from __future__ import annotations

import re
from pathlib import Path

from wxlocal.pipelines.mp_scroll.capture.idb_reader import DEFAULT_PROFILES, read_storage_bytes, find_storage_dirs

SHORT_RE = re.compile(r"https?://mp\.weixin\.qq\.com/s/[A-Za-z0-9_\-]{8,40}")
TITLE_UTF16_HINTS = ("codebase-memory", "LoongSuite", "CyberGym", "Claude Science", "自主渗透")

profiles = DEFAULT_PROFILES
print("profiles", profiles)

# scan each store individually
for store in find_storage_dirs(profiles):
    blob = read_storage_bytes([store])
    text = blob.decode("utf-8", errors="replace")
    short = set(SHORT_RE.findall(text))
    hits = [k for k in TITLE_UTF16_HINTS if k.lower() in text.lower()]
    if short or hits or len(blob) > 100_000:
        print(f"\n{store.parent.name}/{store.name}: blob={len(blob)} short={len(short)} kw={hits}")
        for u in list(short)[:5]:
            print("  short", u)

# full combined
all_blob = read_storage_bytes()
text = all_blob.decode("utf-8", errors="replace")
print("\n=== combined ===")
print("short urls", len(set(SHORT_RE.findall(text))))
for k in TITLE_UTF16_HINTS:
    print(k, k.lower() in text.lower())

# webview + service worker
root = profiles
for pattern in ("webview_*/IndexedDB/*.leveldb", "multitab_*/Session Storage", "multitab_*/Service Worker/Database"):
    for p in root.glob(pattern):
        if p.is_dir():
            blob = read_storage_bytes([p])
            t = blob.decode("utf-8", errors="replace")
            short = set(SHORT_RE.findall(t))
            kw = [k for k in TITLE_UTF16_HINTS if k.lower() in t.lower()]
            if blob:
                print(f"\nextra {p.relative_to(root)}: blob={len(blob)} short={len(short)} kw={kw}")
