"""探测 brandsessionholder / gh_ 消息结构与样例。"""
import hashlib
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
msg_db = ROOT / "decrypted/message/message_0.db"
session_db = ROOT / "decrypted/session/session.db"
contact_db = ROOT / "decrypted/contact/contact.db"


def msg_table(username: str, tables: set[str]) -> str | None:
    t = f"Msg_{hashlib.md5(username.encode()).hexdigest()}"
    return t if t in tables else None


def extract_title(content: str) -> str:
    m = re.search(r"<title>(.*?)</title>", content or "", re.S)
    if not m:
        return ""
    return m.group(1).replace("&amp;", "&").strip()[:120]


conn = sqlite3.connect(msg_db)
tables = {r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
)}

for u in ["brandsessionholder", "brandservicesessionholder", "gh_acfcf1689379"]:
    t = msg_table(u, tables)
    print(f"\n=== {u} table={t} ===")
    if not t:
        continue
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
    print("cols:", cols)
    n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print("count:", n)
    for row in conn.execute(f"SELECT * FROM {t} ORDER BY sort_seq DESC LIMIT 3"):
        d = dict(zip(cols, row))
        content = d.get("message_content") or d.get("compress_content") or ""
        if isinstance(content, bytes):
            content = content[:200].decode("utf-8", errors="replace")
        title = extract_title(str(d.get("message_content") or ""))
        print(" type", d.get("local_type"), "title", title)
        print(" content head", str(content)[:200])

# gh sessions count with messages
conn_s = sqlite3.connect(session_db)
scols = [r[1] for r in conn_s.execute("PRAGMA table_info(SessionTable)")]
gh_with_msg = 0
total_msgs = 0
for row in conn_s.execute("SELECT username FROM SessionTable"):
    u = row[0]
    if not u.startswith("gh_"):
        continue
    t = msg_table(u, tables)
    if t:
        c = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        if c:
            gh_with_msg += 1
            total_msgs += c
print(f"\ngh_ with msgs: {gh_with_msg} total_msgs={total_msgs}")

conn.close()
conn_s.close()
