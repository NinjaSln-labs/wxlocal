"""增量解析指定联系人最新消息并归档。"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from paths import ARCHIVE_ROOT, EXPORTS_DIR, WATCH_CONTACT, ensure_kb_dirs
from ninjasin_dedup import dedup_key, load_known_keys, register_keys, split_new_items

ROOT = Path(__file__).resolve().parent
INPUT = EXPORTS_DIR / f"messages_{WATCH_CONTACT}.json"

_FALLBACK_CUTOFF = "2026-08-25 19:58:18"
_FALLBACK_RULES = [
    ("其它", []),
]


def _load_archive_config() -> tuple[str, list[tuple[str, list[str]]]]:
    import os

    override = os.environ.get("WECHAT_ARCHIVE_RULES", "").strip()
    candidates = []
    if override:
        candidates.append(Path(override))
    candidates.append(ARCHIVE_ROOT.parent / "config" / "archive_rules.json")
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cutoff = str(data.get("cutoff_exclusive") or _FALLBACK_CUTOFF)
            rules_raw = data.get("rules", [])
            rules: list[tuple[str, list[str]]] = []
            if isinstance(rules_raw, list):
                for row in rules_raw:
                    if isinstance(row, dict):
                        rules.append((str(row.get("category", "其它")), list(row.get("keywords", []))))
            if rules:
                return cutoff, rules
        except (json.JSONDecodeError, OSError):
            continue
    return _FALLBACK_CUTOFF, _FALLBACK_RULES


CUTOFF, RULES = _load_archive_config()


def fine_category(title: str) -> str:
    t = title.lower()
    for name, kws in RULES:
        if name == "其它":
            return name
        if any(k.lower() in t for k in kws):
            return name
    return "其它"


def extract_appmsg(content: str) -> dict | None:
    if not content or "<appmsg" not in content:
        return None
    title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", content, re.S)
    title = ""
    if title_m:
        title = title_m.group(1) or title_m.group(2) or ""
        title = html.unescape(title).strip()
    url_m = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>|<url>(.*?)</url>", content, re.S)
    url = ""
    if url_m:
        url = html.unescape((url_m.group(1) or url_m.group(2) or "").strip())
    # finder / 视频号卡片可能没有标准 url
    desc_m = re.search(r"<des><!\[CDATA\[(.*?)\]\]></des>|<des>(.*?)</des>", content, re.S)
    desc = ""
    if desc_m:
        desc = html.unescape((desc_m.group(1) or desc_m.group(2) or "").strip())[:300]
    source_m = re.search(
        r"<sourcedisplayname><!\[CDATA\[(.*?)\]\]></sourcedisplayname>|<sourcedisplayname>(.*?)</sourcedisplayname>",
        content,
        re.S,
    )
    source = ""
    if source_m:
        source = html.unescape((source_m.group(1) or source_m.group(2) or "").strip())
    if not title:
        return None
    return {"title": title, "url": url, "summary": desc, "source_name": source}


def main() -> dict[str, int | str]:
    ensure_kb_dirs()
    if not INPUT.is_file():
        raise SystemExit(f"缺少导出: {INPUT}（请先 export_contact.py {WATCH_CONTACT}）")
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    msgs = data["messages"]
    new_msgs = [m for m in msgs if m.get("time", "") > CUTOFF]

    items = []
    for i, m in enumerate(new_msgs, 1):
        parsed = extract_appmsg(m.get("content") or "")
        if not parsed:
            # 非 appmsg：记为短消息
            raw = (m.get("content") or "").strip()
            if not raw or (raw.startswith("<?xml") and "<appmsg" not in raw):
                continue
            items.append(
                {
                    "index": i,
                    "time": m["time"],
                    "type": "text",
                    "title": raw[:120],
                    "url": "",
                    "summary": "",
                    "source_name": "",
                    "category": "短消息",
                }
            )
            continue
        cat = fine_category(parsed["title"])
        items.append(
            {
                "index": i,
                "time": m["time"],
                "type": "appmsg",
                **parsed,
                "category": cat,
            }
        )

    known = load_known_keys()
    parsed_count = len(items)
    net_new, dups = split_new_items(items, known)
    for i, it in enumerate(net_new, 1):
        it["index"] = i
    items = net_new

    stamp = datetime.now().strftime("%Y-%m-%d")
    batch_dir = ARCHIVE_ROOT / f"{stamp}-delta"
    batch_dir.mkdir(parents=True, exist_ok=True)

    by_cat: dict[str, list] = defaultdict(list)
    for it in items:
        by_cat[it["category"]].append(it)

    # JSON
    payload = {
        "meta": {
            "contact": WATCH_CONTACT,
            "cutoff_exclusive": CUTOFF,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "source_export": str(INPUT),
            "message_count_total": len(msgs),
            "message_count_new": len(new_msgs),
            "item_count": len(items),
            "item_count_parsed": parsed_count,
            "duplicates_skipped": len(dups),
            "categories": {k: len(v) for k, v in sorted(by_cat.items(), key=lambda x: -len(x[1]))},
        },
        "items": items,
        "by_category": dict(by_cat),
    }
    (batch_dir / "delta.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown catalog
    lines = [
        f"# {WATCH_CONTACT} 增量归档 · {stamp}",
        "",
        f"- 截止点（不含）: `{CUTOFF}`（此前合并转发 90 条已归档）",
        f"- 导出总消息: {len(msgs)}",
        f"- 增量消息: {len(new_msgs)} → 可解析 **{parsed_count}** → 去重后 **{len(items)}**（跳过重复 {len(dups)}）",
        f"- 分类数: {len(by_cat)}",
        "",
        "## 分类一览",
        "",
    ]
    for cat, cat_items in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        lines.append(f"### {cat}（{len(cat_items)}）")
        lines.append("")
        for it in cat_items:
            lines.append(f"- **[{it['index']}] {it['title']}**")
            lines.append(f"  - 时间: {it['time']}")
            if it.get("source_name"):
                lines.append(f"  - 来源: {it['source_name']}")
            if it.get("url"):
                lines.append(f"  - 链接: {it['url']}")
            if it.get("summary"):
                lines.append(f"  - 摘要: {it['summary'][:160]}")
            lines.append("")

    (batch_dir / "delta.md").write_text("\n".join(lines), encoding="utf-8")

    # Update archive index
    index_path = ARCHIVE_ROOT / "INDEX.md"
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    prev = ""
    if index_path.exists():
        prev = index_path.read_text(encoding="utf-8")
    entry = (
        f"| {stamp} | `{batch_dir.name}` | {len(items)} | "
        f"去重后新增 {len(items)}；跳过重复 {len(dups)} |\n"
    )
    index_title = f"{WATCH_CONTACT} 归档索引"
    if index_title not in prev:
        prev = (
            f"# {index_title}\n\n"
            "| 日期 | 批次 | 条目 | 说明 |\n"
            "|------|------|------|------|\n"
        )
    # upsert today's delta row
    import re as _re

    row_re = _re.compile(rf"\| {re.escape(stamp)} \| `{re.escape(batch_dir.name)}` \|.*\n")
    if row_re.search(prev):
        prev = row_re.sub(entry, prev)
    else:
        prev = prev.rstrip() + "\n" + entry
    index_path.write_text(prev, encoding="utf-8")

    register_keys(items, known)

    # Manifest pointer for latest
    (ARCHIVE_ROOT / "LATEST.txt").write_text(
        f"{batch_dir.as_posix()}\nitems={len(items)}\ndups_skipped={len(dups)}\n",
        encoding="utf-8",
    )

    print(f"new_msgs={len(new_msgs)} parsed={parsed_count} net_new={len(items)} dups={len(dups)}")
    print(f"archive={batch_dir}")
    for k, v in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        print(f"  {k}: {len(v)}")
    return {
        "parsed": parsed_count,
        "net_new": len(items),
        "dups": len(dups),
        "archive": str(batch_dir),
    }


if __name__ == "__main__":
    main()
