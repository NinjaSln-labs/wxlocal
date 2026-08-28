"""Rescan IDB and backfill triple titles into registry (Phase 2)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wxlocal.pipelines.mp_scroll.capture.idb_reader import url_has_sn
from wxlocal.pipelines.mp_scroll.capture.idb_registry import export_dev_corpus, load_registry, save_registry, scan_once

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def stats(registry: dict) -> dict[str, int]:
    rows = list(registry.get("items", {}).values())
    triple = [r for r in rows if not url_has_sn(r.get("url", ""))]
    return {
        "total": len(rows),
        "triple": len(triple),
        "triple_title": sum(1 for r in triple if r.get("title")),
        "awaiting_sn": sum(1 for r in triple if r.get("status") == "awaiting_sn"),
        "title_idb": sum(1 for r in triple if r.get("status") == "title_idb"),
        "dev_kept": sum(1 for r in rows if r.get("dev_related") and r.get("title")),
    }


def main() -> None:
    before = stats(load_registry())
    print("before:", before)
    scan_once()
    registry = load_registry()
    after = stats(registry)
    save_registry(registry)
    export_dev_corpus(registry)
    print("after:", after)
    cov = 100 * after["triple_title"] / after["triple"] if after["triple"] else 0
    print(f"triple title coverage: {after['triple_title']}/{after['triple']} ({cov:.0f}%)")


if __name__ == "__main__":
    main()
