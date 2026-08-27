"""抓包结果持久化到 F 盘语料库。"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import MP_CAPTURE_ARCHIVE, MP_CAPTURE_EXPORT, MP_CAPTURE_KB, MP_CAPTURE_RAW, ensure_mp_capture_dirs

FLOW_AUDIT = MP_CAPTURE_EXPORT / "flow_audit.jsonl"


def _item_key(item: dict) -> str:
    url = (item.get("url") or "").strip()
    if url:
        return url
    return f"title:{item.get('title', '')}"


def load_store() -> dict:
    ensure_mp_capture_dirs()
    latest = MP_CAPTURE_EXPORT / "mp_capture_latest.json"
    if latest.is_file():
        return json.loads(latest.read_text(encoding="utf-8"))
    return {
        "meta": {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source": "mp_capture mitmproxy",
        },
        "items": [],
        "flows_seen": 0,
    }


def save_store(store: dict) -> None:
    ensure_mp_capture_dirs()
    store["meta"]["updated_at"] = datetime.now().isoformat(timespec="seconds")
    latest = MP_CAPTURE_EXPORT / "mp_capture_latest.json"
    latest.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

    stamp = datetime.now().strftime("%Y-%m-%d")
    day = MP_CAPTURE_ARCHIVE / stamp
    day.mkdir(parents=True, exist_ok=True)
    (day / "mp_capture.json").write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

    (MP_CAPTURE_KB / "INDEX.md").write_text(
        "\n".join(
            [
                "# 公众号 · 抓包语料（推荐流）",
                "",
                f"- 最近更新: `{store['meta'].get('updated_at', '')}`",
                f"- 累计文章: **{len(store.get('items', []))}**",
                f"- 观测请求: {store.get('flows_seen', 0)}",
                f"- 快照: [`exports/mp_capture_latest.json`](exports/mp_capture_latest.json)",
                f"- 今日归档: [`archive/{stamp}/`](archive/{stamp}/)",
                "",
                "启动抓包: `run_mp_capture.bat`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def merge_items(store: dict, new_items: list[dict], flow_meta: dict) -> int:
    index = {_item_key(x): x for x in store.get("items", [])}
    added = 0
    now = datetime.now().isoformat(timespec="seconds")
    for raw in new_items:
        key = _item_key(raw)
        if not key:
            continue
        item = dict(index.get(key, {}))
        item.update({k: v for k, v in raw.items() if v})
        item.setdefault("first_seen", now)
        item["last_seen"] = now
        item.setdefault("hit_count", 0)
        item["hit_count"] = int(item.get("hit_count", 0)) + 1
        if flow_meta:
            item["last_flow"] = flow_meta
        if key not in index:
            added += 1
        index[key] = item
    store["items"] = sorted(index.values(), key=lambda x: x.get("last_seen", ""), reverse=True)
    return added


def append_flow_audit(meta: dict) -> None:
    ensure_mp_capture_dirs()
    with FLOW_AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")


def save_raw_flow(host: str, path: str, body: bytes, content_type: str, *, force: bool = False) -> Path | None:
    limit = 3_000_000 if force else 800_000
    if len(body) > limit:
        return None
    ensure_mp_capture_dirs()
    safe = re.sub(r"[^\w\-.]+", "_", f"{host}{path}")[:120]
    ts = datetime.now().strftime("%H%M%S")
    out = MP_CAPTURE_RAW / f"{ts}_{safe}.txt"
    header = f"# host={host}\n# path={path}\n# content-type={content_type}\n# bytes={len(body)}\n\n"
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        return None
    out.write_text(header + text, encoding="utf-8")
    return out
