"""从已解密数据库导出聊天记录"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import zstd

PROJECT_ROOT = Path(__file__).resolve().parent
DECRYPTED_DIR = PROJECT_ROOT / "decrypted"
OUTPUT_DIR = PROJECT_ROOT / "output"

MSG_DB = DECRYPTED_DIR / "message" / "message_0.db"
SESSION_DB = DECRYPTED_DIR / "session" / "session.db"
CONTACT_DB = DECRYPTED_DIR / "contact" / "contact.db"
OUT = OUTPUT_DIR / "messages.json"


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


def export_all() -> dict:
    if not MSG_DB.is_file():
        raise FileNotFoundError(f"未找到解密数据库: {MSG_DB}")

    contacts = {}
    if CONTACT_DB.is_file():
        conn = sqlite3.connect(str(CONTACT_DB))
        contacts = {r[0]: r[1] for r in conn.execute("SELECT username, nick_name FROM contact") if r[1]}
        conn.close()

    sessions = []
    if SESSION_DB.is_file():
        conn = sqlite3.connect(str(SESSION_DB))
        for row in conn.execute(
            "SELECT username, type, unread_count, summary, last_timestamp FROM SessionTable LIMIT 15"
        ):
            sessions.append({
                "username": row[0],
                "type": row[1],
                "unread": row[2],
                "summary": decompress(row[3]),
                "time": datetime.fromtimestamp(row[4]).strftime("%Y-%m-%d %H:%M:%S") if row[4] else "",
            })
        conn.close()

    conn = sqlite3.connect(str(MSG_DB))
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
        )
    ]
    messages = []
    for table in tables:
        talker_id = table.replace("Msg_", "")
        talker = contacts.get(talker_id, talker_id)
        for row in conn.execute(
            f"SELECT create_time, message_content, compress_content, local_type, real_sender_id "
            f"FROM [{table}] ORDER BY create_time DESC LIMIT 20"
        ):
            content = decompress(row[2] if row[2] else row[1])
            messages.append({
                "time": datetime.fromtimestamp(row[0]).strftime("%Y-%m-%d %H:%M:%S") if row[0] else "",
                "talker": talker,
                "talker_id": talker_id,
                "type": row[3],
                "sender": contacts.get(row[4], row[4]) if row[4] else talker,
                "content": content[:500],
            })
    conn.close()

    messages.sort(key=lambda x: x["time"], reverse=True)
    messages = messages[:30]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    result = {"sessions": sessions, "messages": messages}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def main():
    result = export_all()
    print(f"Sessions: {len(result['sessions'])}")
    print(f"Messages: {len(result['messages'])}")
    print("--- Recent messages ---")
    for m in result["messages"][:10]:
        print(f"[{m['time']}] {m['talker']}: {m['content'][:100]}")


if __name__ == "__main__":
    main()
