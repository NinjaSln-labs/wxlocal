"""导出抓包语料：开发向过滤 + 可选抓正文。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from export_mp_dev import fetch_http_body
from mp_dev_filter import is_dev_related
from paths import MP_CAPTURE_ARCHIVE, MP_CAPTURE_EXPORT, MP_CAPTURE_KB, ensure_mp_capture_dirs
from mp_capture.storage import load_store, save_store


def build_md(meta: dict, items: list[dict]) -> str:
    lines = [
        "# 公众号 · 抓包语料",
        "",
        f"- 导出: {meta.get('exported_at')}",
        f"- 原始: {meta.get('total')} / 开发向: {meta.get('kept')}",
        "",
    ]
    for it in items:
        lines += [
            f"## [{it.get('dev_index')}] {it.get('title', '')}",
            "",
            f"- **来源**: {it.get('source_name', '')}",
            f"- **链接**: {it.get('url', '')}",
            f"- **首次**: {it.get('first_seen', '')}",
            f"- **过滤**: {it.get('filter_reason', '')}",
            "",
        ]
        if it.get("summary"):
            lines += ["**摘要:**", "", it["summary"], ""]
        if it.get("body"):
            lines += ["**正文:**", "", it["body"], ""]
        lines += ["---", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="导出 mitm 抓包公众号语料")
    parser.add_argument("--all", action="store_true", help="不过滤，导出全部")
    parser.add_argument("--fetch-bodies", action="store_true", help="HTTP 抓正文")
    args = parser.parse_args()

    ensure_mp_capture_dirs()
    store = load_store()
    items = list(store.get("items", []))

    kept, dropped = [], []
    for i, it in enumerate(items, 1):
        ok, reason = (True, "all") if args.all else is_dev_related(
            it.get("title", ""), it.get("summary", ""), it.get("source_name", "")
        )
        row = dict(it)
        row["filter_reason"] = reason
        row["index"] = i
        if ok:
            kept.append(row)
        else:
            dropped.append(row)

    for j, it in enumerate(kept, 1):
        it["dev_index"] = j

    if args.fetch_bodies:
        print(f"抓取正文 {len(kept)} 条...")
        for it in kept:
            if it.get("url"):
                body = fetch_http_body(it["url"])
                if body:
                    it["body"] = body
                    it["body_source"] = "HTTP抓取"
                time.sleep(0.5)

    meta = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "source": "mp-capture mitmproxy",
        "filter": "all" if args.all else "mp_dev_filter.py",
        "total": len(items),
        "kept": len(kept),
        "dropped": len(dropped),
        "flows_seen": store.get("flows_seen", 0),
        "body_fetched": sum(1 for i in kept if i.get("body")),
    }

    stamp = datetime.now().strftime("%Y-%m-%d")
    batch = MP_CAPTURE_ARCHIVE / f"{stamp}-capture"
    batch.mkdir(parents=True, exist_ok=True)

    payload = {"meta": meta, "items": kept, "dropped_sample": dropped[:40]}
    out_json = batch / "mp_capture.json"
    out_md = batch / "mp_capture.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(build_md(meta, kept), encoding="utf-8")

    latest = MP_CAPTURE_EXPORT / "mp_capture_latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    save_store(store)

    (MP_CAPTURE_KB / "INDEX.md").write_text(
        "\n".join(
            [
                "# 公众号 · 抓包语料（推荐流）",
                "",
                f"- 最近导出: `{meta['exported_at']}`",
                f"- 累计捕获: {meta['total']} / 开发向 **{meta['kept']}**",
                f"- 批次: [`archive/{batch.name}/`](archive/{batch.name}/)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"total={meta['total']} kept={meta['kept']} flows={meta['flows_seen']}")
    print(f"JSON: {out_json}")
    for it in kept[:12]:
        print(f"  [{it['dev_index']}] {it.get('title', '')[:60]}")


if __name__ == "__main__":
    main()
