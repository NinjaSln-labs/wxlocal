"""列出 session 里所有非好友会话，找推荐流线索。"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
session = sqlite3.connect(ROOT / "decrypted/session/session.db")
contact = sqlite3.connect(ROOT / "decrypted/contact/contact.db")

cols = [r[1] for r in session.execute("PRAGMA table_info(SessionTable)")]
contact_users = {r[0] for r in contact.execute("SELECT username FROM contact")}

print("SessionTable columns:", cols)
print()
for row in session.execute("SELECT * FROM SessionTable ORDER BY username"):
    d = dict(zip(cols, row))
    u = d.get("username") or ""
    summ = str(d.get("summary") or "")[:100]
    if u in contact_users:
        tag = "contact"
    elif u.startswith("gh_"):
        tag = "gh_no_contact"
    elif "brand" in u or u in ("newsapp",):
        tag = "SPECIAL"
    else:
        tag = "no_contact"
    print(f"[{tag}] {u} | {summ}")

session.close()
contact.close()
