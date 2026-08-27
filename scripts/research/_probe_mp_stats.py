"""统计公众号可读体量。"""
import hashlib
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def msg_table(username: str, tables: set[str]) -> str | None:
    t = f"Msg_{hashlib.md5(username.encode()).hexdigest()}"
    return t if t in tables else None


def main() -> None:
    contact = sqlite3.connect(ROOT / "decrypted/contact/contact.db")
    session = sqlite3.connect(ROOT / "decrypted/session/session.db")
    biz = sqlite3.connect(ROOT / "decrypted/message/biz_message_0.db")
    msg0 = sqlite3.connect(ROOT / "decrypted/message/message_0.db")

    gh_contacts = [r[0] for r in contact.execute("SELECT username FROM contact WHERE username LIKE 'gh_%'")]
    print(f"contact.db gh_ 联系人: {len(gh_contacts)}")

    sess_cols = [r[1] for r in session.execute("PRAGMA table_info(SessionTable)")]
    gh_sessions = []
    for row in session.execute("SELECT * FROM SessionTable"):
        d = dict(zip(sess_cols, row))
        u = d.get("username") or ""
        if u.startswith("gh_"):
            gh_sessions.append((u, str(d.get("summary") or "")))
    print(f"session.db gh_ 会话: {len(gh_sessions)}")

    biz_accounts = list(biz.execute("SELECT user_name, is_session FROM Name2Id"))
    biz_set = {u for u, _ in biz_accounts}
    biz_gh = [u for u, _ in biz_accounts if u.startswith("gh_")]
    print(f"biz_message Name2Id: 总 {len(biz_accounts)}, gh_ {len(biz_gh)}")

    biz_tables = {r[0] for r in biz.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")}
    total_msgs = 0
    no_table = []
    per_account = []
    for u, _ in biz_accounts:
        t = msg_table(u, biz_tables)
        if t:
            c = biz.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            total_msgs += c
            if c:
                per_account.append((u, c))
        else:
            no_table.append(u)
    print(f"biz_message 消息行: {total_msgs}")
    print(f"biz 无 Msg 表: {len(no_table)} -> {no_table[:8]}")

    msg0_tables = {r[0] for r in msg0.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")}
    msg0_gh_rows = 0
    msg0_gh_accounts = 0
    for u in gh_contacts:
        t = msg_table(u, msg0_tables)
        if t:
            c = msg0.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            if c:
                msg0_gh_accounts += 1
                msg0_gh_rows += c
    print(f"message_0.db gh_ 有消息: {msg0_gh_accounts} 号 / {msg0_gh_rows} 条")

    sess_not_biz = [(u, s) for u, s in gh_sessions if u not in biz_set]
    print(f"session 有但 biz 无 Name2Id: {len(sess_not_biz)}")
    if sess_not_biz[:5]:
        for u, s in sess_not_biz[:5]:
            print(f"  {u}: {s[:60]}")

    for special in ["brandsessionholder", "brandservicesessionholder", "newsapp"]:
        row = session.execute("SELECT username, summary FROM SessionTable WHERE username=?", (special,)).fetchone()
        if row:
            print(f"session {special}: {str(row[1])[:120]}")

    # time range in biz
    times = []
    for u, c in per_account:
        t = msg_table(u, biz_tables)
        for ts, in biz.execute(f"SELECT create_time FROM [{t}]"):
            if ts:
                times.append(ts)
    if times:
        from datetime import datetime

        print(f"biz 时间跨度: {datetime.fromtimestamp(min(times))} ~ {datetime.fromtimestamp(max(times))}")

    contact.close()
    session.close()
    biz.close()
    msg0.close()


if __name__ == "__main__":
    main()
