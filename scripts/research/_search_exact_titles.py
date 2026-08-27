"""Exact search for two article titles."""
from __future__ import annotations

import html
import re
import sqlite3
import zstd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIZ = ROOT / "decrypted/message/biz_message_0.db"

EXACT = [
    "虚拟机已困不住",
    "网络攻击能力的智能体",
    "清华徐恪",
    "大模型安全不是给模型加个护栏",
    "从芯片到智能体的全链路",
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


def main() -> None:
    print("=== exact biz_message ===")
    conn = sqlite3.connect(BIZ)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")]
    for kw in EXACT:
        found = False
        for t in tables:
            for sort_seq, content in conn.execute(f'SELECT sort_seq, message_content FROM "{t}"'):
                text = dec(content)
                if kw not in text:
                    continue
                m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", text, re.S)
                title = html.unescape((m.group(1) or m.group(2) or "").strip()) if m else ""
                um = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>|<url>(.*?)</url>", text, re.S)
                url = html.unescape((um.group(1) or um.group(2) or "").strip()) if um else ""
                print(f"HIT [{kw}] {title}")
                print(f"  {url}")
                print(f"  table={t} sort_seq={sort_seq}")
                found = True
                break
            if found:
                break
        if not found:
            print(f"MISS [{kw}]")

    print("\n=== recent 5 biz by sort_seq ===")
    recent = []
    for t in tables:
        try:
            row = conn.execute(f'SELECT sort_seq, message_content FROM "{t}" ORDER BY sort_seq DESC LIMIT 1').fetchone()
        except sqlite3.Error:
            continue
        if not row:
            continue
        sort_seq, content = row
        text = dec(content)
        if "<title>" not in text:
            continue
        m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", text, re.S)
        title = html.unescape((m.group(1) or m.group(2) or "").strip()) if m else ""
        recent.append((sort_seq, title, t))
    recent.sort(reverse=True)
    from datetime import datetime

    for sort_seq, title, t in recent[:8]:
        print(datetime.fromtimestamp(sort_seq / 1000), title[:75])

    conn.close()


if __name__ == "__main__":
    main()
