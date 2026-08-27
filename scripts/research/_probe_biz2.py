"""统计 biz_message 体量并解码样例。"""
import hashlib
import sqlite3
import zstd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
biz_db = ROOT / "decrypted/message/biz_message_0.db"
contact_db = ROOT / "decrypted/contact/contact.db"


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


conn = sqlite3.connect(biz_db)
tables = {r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
)}
name2id = [(r[0], r[1]) for r in conn.execute("SELECT user_name, is_session FROM Name2Id")]

contacts = {}
if contact_db.is_file():
    c = sqlite3.connect(contact_db)
    contacts = {r[0]: r[1] for r in c.execute("SELECT username, nick_name FROM contact")}
    c.close()

total = 0
for u, _ in name2id:
    t = f"Msg_{hashlib.md5(u.encode()).hexdigest()}"
    if t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        total += n
print("gh accounts in biz Name2Id:", len(name2id))
print("total messages:", total)

# brandsession tables
for u in ["brandsessionholder", "brandservicesessionholder"]:
    t = f"Msg_{hashlib.md5(u.encode()).hexdigest()}"
    print(u, "table", t, "exists", t in tables)
    if t in tables:
        print("  count", conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0])

# decode gh_acfcf1689379 (github article)
u = "gh_acfcf1689379"
t = f"Msg_{hashlib.md5(u.encode()).hexdigest()}"
print("\n", u, contacts.get(u), t)
row = conn.execute(
    f"SELECT message_content, compress_content, create_time FROM [{t}] ORDER BY create_time DESC LIMIT 1"
).fetchone()
text = decompress(row[1] if row[1] else row[0])
print(text[:800])

conn.close()
