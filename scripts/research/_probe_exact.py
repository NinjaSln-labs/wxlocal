"""在 message_0 + biz_message 精确搜 3 篇标题。"""
import hashlib
import html
import re
import sqlite3
import zstd
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EXACT = [
    "SkillForge",
    "自蒸馏",
    "OpenObserve",
    "Vortex",
    "告别向量库",
    "RING",
    "塞进模型参数",
]


def decompress(data):
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


def scan_db(db_path: Path, label: str) -> None:
    conn = sqlite3.connect(db_path)
    if "biz_message" in label:
        name2id = {r[0]: r[1] for r in conn.execute("SELECT user_name, is_session FROM Name2Id")}
    else:
        name2id = {}
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")]
    print(f"\n=== {label} ({len(tables)} tables) ===")
    found = 0
    for t in tables:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
        for row in conn.execute(f"SELECT * FROM [{t}]"):
            d = dict(zip(cols, row))
            content = decompress(d.get("compress_content") or d.get("message_content"))
            hits = [k for k in EXACT if k.lower() in content.lower()]
            if not hits:
                continue
            # filter RING false positive: need 向量 or SkillForge context
            if hits == ["RING"] and "向量" not in content and "RAG" not in content:
                continue
            found += 1
            ts = d.get("create_time") or 0
            title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", content, re.S)
            title = html.unescape(title_m.group(1).strip()) if title_m else content[:120]
            url_m = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>", content, re.S)
            url = html.unescape(url_m.group(1).strip()) if url_m else ""
            print(f"\n  HIT keys={hits}")
            print(f"  table={t} time={datetime.fromtimestamp(ts) if ts else ''}")
            print(f"  title={title[:100]}")
            if url:
                print(f"  url={url[:100]}")
            else:
                print(f"  snippet={content[:200].replace(chr(10),' ')}")
    if not found:
        print("  （无精确命中）")
    conn.close()


def main():
    scan_db(ROOT / "decrypted/message/biz_message_0.db", "biz_message_0.db")
    scan_db(ROOT / "decrypted/message/message_0.db", "message_0.db")


if __name__ == "__main__":
    main()
