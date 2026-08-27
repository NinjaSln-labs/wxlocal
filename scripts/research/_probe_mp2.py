"""继续探测：订阅号消息盒、gh_ 会话是否有消息表。"""
import hashlib
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
contact_db = ROOT / "decrypted/contact/contact.db"
session_db = ROOT / "decrypted/session/session.db"
msg_db = ROOT / "decrypted/message/message_0.db"


def msg_table_for(username: str, tables: set[str]) -> str | None:
    t = f"Msg_{hashlib.md5(username.encode()).hexdigest()}"
    return t if t in tables else None


def main() -> None:
    conn = sqlite3.connect(session_db)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(SessionTable)")]
    print("SessionTable cols:", cols)
    rows = conn.execute("SELECT * FROM SessionTable ORDER BY sort_timestamp DESC").fetchall()
    print(f"sessions: {len(rows)}")
    for row in rows[:30]:
        d = dict(zip(cols, row))
        u = d.get("username", "")
        s = (d.get("summary") or "")[:60]
        print(f"  {d.get('type'):>3} | {u[:40]:40} | {s}")
    # keyword sessions
    keys = ("gh_", "news", "biz", "brand", "mp", "订阅", "公众号", "official")
    print("\n--- keyword sessions ---")
    for row in rows:
        d = dict(zip(cols, row))
        u = str(d.get("username") or "")
        s = str(d.get("summary") or "")
        if any(k in (u + s).lower() for k in keys) or u.startswith("gh_"):
            print(dict((k, d[k]) for k in cols if k in ("username", "type", "summary", "last_timestamp")))
    conn.close()

    conn = sqlite3.connect(contact_db)
    if "biz_info" in [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
        bcols = [r[1] for r in conn.execute("PRAGMA table_info(biz_info)")]
        print("\nbiz_info cols:", bcols)
        n = conn.execute("SELECT COUNT(*) FROM biz_info").fetchone()[0]
        print("biz_info rows:", n)
        for row in conn.execute("SELECT * FROM biz_info LIMIT 5"):
            print(" ", dict(zip(bcols, row)))
    conn.close()

    conn = sqlite3.connect(msg_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
    )}
    name2id = {r[0]: r[1] for r in conn.execute("SELECT user_name, rowid FROM Name2Id")}

    # sample gh with session
    conn_s = sqlite3.connect(session_db)
    scols = [r[1] for r in conn_s.execute("PRAGMA table_info(SessionTable)")]
    gh_sessions = []
    for row in conn_s.execute("SELECT * FROM SessionTable"):
        d = dict(zip(scols, row))
        u = d.get("username") or ""
        if u.startswith("gh_"):
            gh_sessions.append(u)
    conn_s.close()
    print(f"\ngh_ sessions in SessionTable: {len(gh_sessions)}")
    for u in gh_sessions[:8]:
        t = msg_table_for(u, tables)
        cnt = 0
        if t:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {u} table={t} msgs={cnt}")

    # common subscription inbox usernames on WeChat
    candidates = [
        "newsapp", "brandsessionholder", "brandservicesessionholder",
        "notifymessage", "mphelper", "weixin", "filehelper", "<your_wxid>",
    ]
    print("\n--- known candidate usernames ---")
    for u in candidates:
        t = msg_table_for(u, tables)
        in_session = u in [r[0] for r in sqlite3.connect(session_db).execute("SELECT username FROM SessionTable")]
        cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if t else 0
        print(f"  {u:30} session={in_session} table={t} msgs={cnt}")

    conn.close()


if __name__ == "__main__":
    main()
