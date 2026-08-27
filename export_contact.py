"""导出指定联系人的聊天记录"""
import argparse
import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import zstd

from paths import EXPORTS_DIR, OUTPUT_DIR, WATCH_CONTACT, ensure_kb_dirs

PROJECT_ROOT = Path(__file__).resolve().parent
DECRYPTED_DIR = PROJECT_ROOT / "decrypted"
MSG_DB = DECRYPTED_DIR / "message" / "message_0.db"
CONTACT_DB = DECRYPTED_DIR / "contact" / "contact.db"


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


def find_contact(name: str) -> tuple[str, str]:
    conn = sqlite3.connect(str(CONTACT_DB))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(contact)")]
    for row in conn.execute("SELECT * FROM contact"):
        d = dict(zip(cols, row))
        haystack = " ".join(str(v) for v in d.values() if v).lower()
        if name.lower() in haystack:
            conn.close()
            return d["username"], d.get("nick_name", d["username"])
    conn.close()
    raise ValueError(f"未找到联系人: {name}")


def export_contact(name: str, limit: int = 0) -> dict:
    username, nick = find_contact(name)
    print(f"[+] 联系人: {nick} ({username})")

    conn = sqlite3.connect(str(MSG_DB))
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
    )]

    # 表名可能是 Msg_<hash>，通过 Name2Id 映射
    name2id = {}
    try:
        for row in conn.execute("SELECT user_name, rowid FROM Name2Id"):
            name2id[row[0]] = row[1]
    except sqlite3.OperationalError:
        pass

    target_table = f"Msg_{hashlib.md5(username.encode()).hexdigest()}"
    if target_table not in tables:
        target_table = None
        for t in tables:
            tid = t.replace("Msg_", "")
            if tid == username:
                target_table = t
                break

    if not target_table:
        conn.close()
        raise ValueError(f"未找到 {username} 的消息表，可用表: {tables[:10]}")

    print(f"[+] 消息表: {target_table}")

    contacts = {}
    if CONTACT_DB.is_file():
        cconn = sqlite3.connect(str(CONTACT_DB))
        contacts = {r[0]: r[1] for r in cconn.execute("SELECT username, nick_name FROM contact") if r[1]}
        cconn.close()

    sql = (
        f"SELECT create_time, message_content, compress_content, local_type, real_sender_id "
        f"FROM [{target_table}] ORDER BY create_time DESC"
    )
    if limit > 0:
        sql += f" LIMIT {limit}"

    messages = []
    for row in conn.execute(sql):
        content = decompress(row[2] if row[2] else row[1])
        sender_id = row[4]
        is_self = sender_id == 1 or str(sender_id) == username
        messages.append({
            "time": datetime.fromtimestamp(row[0]).strftime("%Y-%m-%d %H:%M:%S") if row[0] else "",
            "talker": nick,
            "talker_id": username,
            "type": row[3],
            "sender": "我" if is_self else contacts.get(str(sender_id), str(sender_id)),
            "content": content,
        })
    conn.close()

    messages.sort(key=lambda x: x["time"])
    result = {
        "contact": {"username": username, "nick_name": nick},
        "message_count": len(messages),
        "messages": messages,
    }

    safe_name = nick.replace("/", "_")
    ensure_kb_dirs()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Named contact → KB exports; others stay in ./output/
    if safe_name.lower() == WATCH_CONTACT.lower():
        out_path = EXPORTS_DIR / f"messages_{safe_name}.json"
    else:
        out_path = OUTPUT_DIR / f"messages_{safe_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[+] 导出 {len(messages)} 条消息到 {out_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description="导出指定联系人聊天记录")
    parser.add_argument("name", help="联系人昵称/备注/wxid")
    parser.add_argument("--limit", type=int, default=0, help="限制条数，0=全部")
    args = parser.parse_args()
    result = export_contact(args.name, args.limit)
    print(f"\n--- 最近 10 条 ---")
    for m in result["messages"][-10:]:
        print(f"[{m['time']}] {m['sender']}: {m['content'][:120]}")


if __name__ == "__main__":
    main()
