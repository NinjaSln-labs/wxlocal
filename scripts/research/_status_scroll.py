"""Quick status after user scroll."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime

from wxlocal.pipelines.mp_scroll.capture.idb_reader import article_key, scan_live, url_has_sn
from wxlocal.pipelines.mp_scroll.capture.idb_registry import load_registry

cards, blob = scan_live()
reg = load_registry()
items = list(reg["items"].values())

by_kind = Counter(i.get("url_kind", "full" if url_has_sn(i.get("url", "")) else "triple") for i in items)
by_status = Counter(i.get("status", "?") for i in items)

recent = sorted(items, key=lambda x: x.get("last_seen", ""), reverse=True)[:12]
dev = [i for i in items if i.get("dev_related") and i.get("title")]

print("=== live scan ===")
print(f"cards={len(cards)} blob={blob} registry={len(items)}")
print(f"kind={dict(by_kind)} status={dict(by_status)}")
print(f"titles={sum(1 for i in items if i.get('title'))} dev_titled={len(dev)}")

print("\n=== recent last_seen ===")
for it in recent:
    t = (it.get("title") or "(no title)")[:55]
    kind = it.get("url_kind", "?")
    print(f"  {it.get('last_seen')} [{kind}] {t}")

print("\n=== dev sample (latest 8) ===")
dev.sort(key=lambda x: x.get("fetched_at") or x.get("last_seen", ""), reverse=True)
for it in dev[:8]:
    print(f"  {(it.get('title') or '')[:70]}")
