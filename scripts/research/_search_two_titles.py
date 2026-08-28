"""Search user-provided titles in biz_message and registry."""
from __future__ import annotations

import html
import json
import re
import sqlite3
import zstd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIZ = ROOT / "decrypted/message/biz_message_0.db"
REG = Path(r"F:\ext\knowledge-base\wechat\mp-capture\registry\idb_registry.json")

QUERIES = [
    ["虚拟机", "网络攻击", "智能体"],
    ["徐恪", "大模型安全", "全链路", "芯片"],
]


def dec(data) -> str:
    if not data:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, bytes):
        if data[:4] == b"\x28\xb5\x2f\xfd":
            try:
                return zstd.decompress(data).decode("utf-8", errors="replace")
            except Exception:
                pass
        return data.decode("utf-8", errors="replace")
    return str(data)


def search_biz() -> None:
    print("=== biz_message ===")
    if not BIZ.is_file():
        print("missing biz db")
        return
    conn = sqlite3.connect(BIZ)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")]
    hits = []
    for t in tables:
        try:
            rows = conn.execute(f'SELECT sort_seq, message_content FROM "{t}"').fetchall()
        except sqlite3.Error:
            continue
        for sort_seq, content in rows:
            text = dec(content)
            blob = text.lower()
            for keys in QUERIES:
                if all(k.lower() in blob or k in text for k in keys[:2]) or any(k in text for k in keys):
                    m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", text, re.S)
                    title = html.unescape((m.group(1) or m.group(2) or "").strip()) if m else ""
                    um = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>|<url>(.*?)</url>", text, re.S)
                    url = html.unescape((um.group(1) or um.group(2) or "").strip()) if um else ""
                    if title or any(k in text for k in keys):
                        hits.append((sort_seq, title, url, t, keys[0]))
    conn.close()
    hits.sort(reverse=True)
    if not hits:
        print("  no hits")
    for row in hits[:20]:
        print(" ", row)


def search_registry() -> None:
    print("\n=== registry titles/urls ===")
    if not REG.is_file():
        print("missing registry")
        return
    data = json.loads(REG.read_text(encoding="utf-8"))
    found = 0
    for item in data.get("items", {}).values():
        hay = f"{item.get('title','')} {item.get('url','')} {item.get('body','')}"
        for keys in QUERIES:
            if any(k in hay for k in keys):
                print(" ", item.get("title") or "(no title)", item.get("url", "")[:90])
                found += 1
    if not found:
        print("  no hits (titles mostly empty)")


def search_idb_blob() -> None:
    print("\n=== idb blob text ===")
    from wxlocal.pipelines.mp_scroll.capture.idb_reader import read_idb_bytes

    blob = read_idb_bytes().decode("utf-8", errors="replace")
    for keys in QUERIES:
        for k in keys:
            print(f"  {k}: {'HIT' if k in blob else 'no'}")


if __name__ == "__main__":
    search_biz()
    search_registry()
    search_idb_blob()
