"""按用户提供的标题关键词全库搜索。"""
from __future__ import annotations

import hashlib
import html
import re
import sqlite3
import zstd
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DECRYPTED = ROOT / "decrypted"

QUERIES = [
    ("SkillForge", ["SkillForge", "自蒸馏", "测试自蒸馏"]),
    ("OpenObserve", ["OpenObserve", "v0.92", "Vortex", "MCP和Vortex"]),
    ("RING RAG", ["RING", "告别向量库", "塞进模型参数"]),
]


def decompress(data) -> str:
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


def extract_fields(content: str) -> dict:
    title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", content, re.S)
    title = html.unescape(title_m.group(1).strip()) if title_m else ""
    url_m = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>", content, re.S)
    url = html.unescape(url_m.group(1).strip()) if url_m else ""
    return {"title": title, "url": url}


def search_biz() -> list[dict]:
    biz = sqlite3.connect(DECRYPTED / "message/biz_message_0.db")
    contact = sqlite3.connect(DECRYPTED / "contact/contact.db")
    contacts = {r[0]: r[1] for r in contact.execute("SELECT username, nick_name FROM contact")}
    tables = {
        r[0]
        for r in biz.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
    }
    hits = []
    for u, _ in biz.execute("SELECT user_name, is_session FROM Name2Id"):
        t = f"Msg_{hashlib.md5(u.encode()).hexdigest()}"
        if t not in tables:
            continue
        cols = [r[1] for r in biz.execute(f"PRAGMA table_info({t})")]
        for row in biz.execute(f"SELECT * FROM [{t}]"):
            d = dict(zip(cols, row))
            content = decompress(d.get("compress_content") or d.get("message_content"))
            blob = content
            for label, kws in QUERIES:
                if any(k.lower() in blob.lower() for k in kws):
                    parsed = extract_fields(content)
                    ts = d.get("create_time") or 0
                    hits.append(
                        {
                            "where": "biz_message",
                            "query": label,
                            "time": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "",
                            "account": contacts.get(u, u),
                            "username": u,
                            **parsed,
                        }
                    )
    biz.close()
    contact.close()
    return hits


def search_session() -> list[dict]:
    session = sqlite3.connect(DECRYPTED / "session/session.db")
    cols = [r[1] for r in session.execute("PRAGMA table_info(SessionTable)")]
    hits = []
    for row in session.execute("SELECT * FROM SessionTable"):
        d = dict(zip(cols, row))
        summ = str(d.get("summary") or "")
        u = d.get("username") or ""
        for label, kws in QUERIES:
            if any(k.lower() in summ.lower() for k in kws):
                hits.append({"where": "session", "query": label, "username": u, "title": summ, "url": ""})
    session.close()
    return hits


def search_all_dbs() -> list[dict]:
    hits = []
    for db in sorted(DECRYPTED.rglob("*.db")):
        try:
            conn = sqlite3.connect(db)
        except Exception:
            continue
        rel = str(db.relative_to(ROOT))
        for table in [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info([{table}])")]
            for col in cols:
                try:
                    for row in conn.execute(f"SELECT [{col}] FROM [{table}]"):
                        val = row[0]
                        if val is None:
                            continue
                        s = val.decode("utf-8", errors="replace") if isinstance(val, bytes) else str(val)
                        for label, kws in QUERIES:
                            if any(k.lower() in s.lower() for k in kws):
                                hits.append(
                                    {
                                        "where": f"{rel}::{table}.{col}",
                                        "query": label,
                                        "snippet": s[:200].replace("\n", " "),
                                    }
                                )
                except Exception:
                    pass
        conn.close()
    return hits


def main() -> None:
    print("=== biz_message 命中 ===")
    biz_hits = search_biz()
    if not biz_hits:
        print("  （无）")
    for h in biz_hits:
        print(f"  [{h['query']}] {h['time']} | {h['account']} | {h['title'][:80]}")
        if h.get("url"):
            print(f"    {h['url'][:100]}")

    print("\n=== session 命中 ===")
    sess_hits = search_session()
    if not sess_hits:
        print("  （无）")
    for h in sess_hits:
        print(f"  [{h['query']}] {h['username']}: {h['title'][:100]}")

    print("\n=== 全 decrypted/*.db 文本命中 ===")
    all_hits = search_all_dbs()
    # 去重
    seen = set()
    uniq = []
    for h in all_hits:
        key = (h["where"], h["query"], h.get("snippet", "")[:80])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    if not uniq:
        print("  （无）")
    for h in uniq[:30]:
        print(f"  [{h['query']}] {h['where']}")
        print(f"    {h.get('snippet','')[:160]}")

    print(f"\n汇总: biz={len(biz_hits)} session={len(sess_hits)} all_db={len(uniq)}")


if __name__ == "__main__":
    main()
