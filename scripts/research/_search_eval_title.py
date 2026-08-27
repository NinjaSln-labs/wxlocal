"""Exact search for Eval article title."""
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
FLOW = Path(r"F:\ext\knowledge-base\wechat\mp-capture\exports\flow_audit.jsonl")

NEEDLES = [
    "Eval：有了",
    "什么叫好",
    "放心上线",
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
    conn = sqlite3.connect(BIZ)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")]
    for kw in NEEDLES:
        found = False
        for t in tables:
            for sort_seq, content in conn.execute(f'SELECT sort_seq, message_content FROM "{t}"'):
                text = dec(content)
                if kw not in text:
                    continue
                m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", text, re.S)
                title = html.unescape((m.group(1) or m.group(2) or "").strip()) if m else ""
                print("HIT", kw, title)
                found = True
                break
            if found:
                break
        if not found:
            print("MISS", kw)
    conn.close()


def search_registry_and_flow() -> None:
    print("\n=== registry ===")
    if REG.is_file():
        text = REG.read_text(encoding="utf-8")
        for kw in NEEDLES:
            print(kw, "HIT" if kw in text else "MISS")
    print("\n=== flow audit after 13:50 ===")
    if FLOW.is_file():
        for line in FLOW.read_text(encoding="utf-8").splitlines():
            if "2026-08-27T13:5" not in line and "2026-08-27T13:49:1" not in line:
                continue
            if any(x in line for x in ("geticon", "115849", "239069", "/s?")):
                print(line[:220])


if __name__ == "__main__":
    search_biz()
    search_registry_and_flow()
