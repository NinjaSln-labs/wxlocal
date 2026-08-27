"""探测本地库是否含公众号/订阅号会话与消息。"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
contact_db = ROOT / "decrypted/contact/contact.db"
session_db = ROOT / "decrypted/session/session.db"
msg_db = ROOT / "decrypted/message/message_0.db"


def main() -> None:
    for label, db in [("contact", contact_db), ("session", session_db), ("message", msg_db)]:
        print(f"=== {label} exists={db.is_file()} ===")
        if not db.is_file():
            continue
        conn = sqlite3.connect(db)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        print("tables:", tables)
        conn.close()

    conn = sqlite3.connect(contact_db)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(contact)")]
    print("contact cols:", cols)

    gh = []
    mp_keywords = []
    for row in conn.execute("SELECT * FROM contact"):
        d = dict(zip(cols, row))
        u = str(d.get("username") or "")
        nick = str(d.get("nick_name") or "")
        alias = str(d.get("alias") or "")
        remark = str(d.get("remark") or "")
        hay = nick + alias + remark + u
        if u.startswith("gh_"):
            gh.append((nick, u))
        if any(k in hay for k in ("公众号", "订阅号", "服务号", "Official")):
            mp_keywords.append((nick, u, alias, remark))
    print(f"gh_ contacts: {len(gh)}")
    for x in gh[:10]:
        print(" ", x)
    print(f"keyword contacts: {len(mp_keywords)}")
    for x in mp_keywords[:10]:
        print(" ", x)
    conn.close()

    if session_db.is_file():
        conn = sqlite3.connect(session_db)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for t in tables:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"session.{t} rows={n} cols={cols[:12]}")
            if n:
                row = conn.execute(f"SELECT * FROM {t} LIMIT 1").fetchone()
                print("  sample:", row[:8] if row else None)
        conn.close()

    # search message tables for appmsg titles from gh sources in NinjaSin export pattern
    if msg_db.is_file():
        conn = sqlite3.connect(msg_db)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
        )]
        print(f"Msg_* tables: {len(tables)}")
        # Name2Id
        try:
            for row in conn.execute("SELECT user_name, rowid FROM Name2Id LIMIT 20"):
                print(" Name2Id:", row)
        except Exception as e:
            print(" Name2Id err:", e)
        conn.close()


if __name__ == "__main__":
    main()
