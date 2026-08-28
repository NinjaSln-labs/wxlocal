"""One-shot batch body enrich for registry items with sn + title."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wxlocal.pipelines.mp_scroll.capture.idb_reader import url_has_sn
from wxlocal.pipelines.mp_scroll.capture.idb_registry import (
    enrich_body_pending,
    export_dev_corpus,
    load_registry,
    proxy_ready,
    save_registry,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def baseline(registry: dict) -> dict[str, int]:
    rows = list(registry.get("items", {}).values())
    dev_full = [
        r
        for r in rows
        if r.get("dev_related") and url_has_sn(r.get("url", ""))
    ]
    return {
        "total": len(rows),
        "dev_full": len(dev_full),
        "dev_full_body": sum(1 for r in dev_full if len(r.get("body") or "") > 200),
    }


def main() -> None:
    if not proxy_ready():
        raise SystemExit("proxy 6696 not reachable")

    registry = load_registry()
    before = baseline(registry)
    print("before:", before)

    rounds = 0
    total_bodies = 0
    while rounds < 20:
        stats = enrich_body_pending(registry, limit=20)
        save_registry(registry)
        rounds += 1
        total_bodies += stats.get("bodies", 0)
        print(f"round {rounds}: {stats}")
        if stats.get("fetched", 0) == 0 or stats.get("bodies", 0) == 0:
            break

    export = export_dev_corpus(registry)
    after = baseline(registry)
    print("after:", after)
    print("export dev_kept:", export["dev_kept"])
    print("total bodies fetched:", total_bodies)


if __name__ == "__main__":
    main()
