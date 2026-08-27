"""从解密后的数据库读取聊天记录"""
import json
import os
import sqlite3
import zstd
from datetime import datetime


def decompress_content(data) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, bytes):
        if data[:4] == b"\x28\xb5\x2f\xfd":  # zstd magic
            try:
                return zstd.decompress(data).decode("utf-8", errors="replace")
            except Exception:
                pass
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return f"[binary {len(data)} bytes]"
    return str(data)


def list_tables(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    return tables


def read_sessions(session_db: str, limit: int = 30) -> list[dict]:
    conn = sqlite3.connect(session_db)
    conn.row_factory = sqlite3.Row
    tables = list_tables(session_db)

    for table in ("SessionTable", "session", "Session"):
        if table in tables:
            cols = [d[1] for d in conn.execute(f"PRAGMA table_info([{table}])")]
            cur = conn.execute(f"SELECT * FROM [{table}] LIMIT ?", (limit,))
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows

    conn.close()
    return []


def read_messages(msg_db: str, limit: int = 50, talker: str = "") -> list[dict]:
    conn = sqlite3.connect(msg_db)
    conn.row_factory = sqlite3.Row
    tables = list_tables(msg_db)

    results = []

    # 微信 4.x 可能用 Msg_ 前缀表或统一 message 表
    msg_tables = [t for t in tables if t.startswith("Msg_")]
    if not msg_tables and "message" in tables:
        msg_tables = ["message"]

    for table in msg_tables:
        cols = {d[1] for d in conn.execute(f"PRAGMA table_info([{table}])")}

        # 适配不同列名
        talker_col = next((c for c in ("StrTalker", "talker", "username") if c in cols), None)
        content_col = next((c for c in ("StrContent", "message_content", "content") if c in cols), None)
        compress_col = "compress_content" if "compress_content" in cols else None
        time_col = next((c for c in ("CreateTime", "create_time") if c in cols), None)
        sender_col = next((c for c in ("IsSender", "is_sender") if c in cols), None)
        type_col = next((c for c in ("Type", "local_type", "type") if c in cols), None)

        if not time_col:
            continue

        select_cols = ["rowid"]
        for c in (talker_col, content_col, compress_col, time_col, sender_col, type_col):
            if c:
                select_cols.append(c)

        where, params = "", []
        if talker and talker_col:
            where = f"WHERE [{talker_col}] = ?"
            params.append(talker)

        sql = f"SELECT {', '.join(f'[{c}]' for c in select_cols)} FROM [{table}] {where} ORDER BY [{time_col}] DESC LIMIT ?"
        params.append(limit)

        for row in conn.execute(sql, params):
            d = dict(row)
            content = d.get(content_col) if content_col else ""
            if compress_col and d.get(compress_col):
                content = decompress_content(d[compress_col])
            elif content:
                content = decompress_content(content)

            ts = d.get(time_col, 0)
            try:
                time_str = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                time_str = str(ts)

            is_sender = d.get(sender_col, 0) if sender_col else 0
            results.append({
                "time": time_str,
                "talker": d.get(talker_col, table) if talker_col else table,
                "sender": "我" if is_sender else d.get(talker_col, "对方"),
                "type": d.get(type_col, 1) if type_col else 1,
                "content": content,
            })

    conn.close()
    results.sort(key=lambda x: x["time"], reverse=True)
    return results[:limit]


def export_json(messages: list[dict], path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
