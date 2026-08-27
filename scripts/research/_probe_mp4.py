"""查找 gh / brandsession 消息实际落在哪张 Msg 表。"""
import hashlib
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
msg_db = ROOT / "decrypted/message/message_0.db"
session_db = ROOT / "decrypted/session/session.db"
contact_db = ROOT / "decrypted/contact/contact.db"

conn = sqlite3.connect(msg_db)
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
)]

name2id = {r[0]: r[1] for r in conn.execute("SELECT user_name, rowid FROM Name2Id")}
print("Name2Id count", len(name2id))
for k in ["brandsessionholder", "brandservicesessionholder", "gh_acfcf1689379", "gh_44c7094d7547", "<your_wxid>"]:
    print(f"  {k}: rowid={name2id.get(k)} md5={hashlib.md5(k.encode()).hexdigest()}")

gh_in_name2id = [(k, v) for k, v in name2id.items() if k.startswith("gh_")]
print("gh_ in Name2Id:", len(gh_in_name2id))
for k, v in gh_in_name2id[:10]:
    print(" ", k, v)

# map rowid to table? maybe Msg tables use rowid not md5
for t in tables:
    try:
        n = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    except Exception:
        continue
    if n > 0:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
        if "real_sender_id" in cols or "create_time" in cols:
            pass
        # sample search for github in content
        for col in ("message_content", "compress_content"):
            if col not in cols:
                continue
            try:
                row = conn.execute(
                    f"SELECT {col} FROM [{t}] WHERE CAST({col} AS TEXT) LIKE '%github%' LIMIT 1"
                ).fetchone()
                if row and row[0]:
                    print(f"HIT github in {t}.{col}")
            except Exception:
                pass

# Try table name = Msg_<rowid>?
for k, rid in list(gh_in_name2id)[:5]:
    for cand in [f"Msg_{rid}", f"Msg_{hashlib.md5(k.encode()).hexdigest()}"]:
        if cand in tables:
            n = conn.execute(f"SELECT COUNT(*) FROM [{cand}]").fetchone()[0]
            print(f"FOUND {cand} for {k} rows={n}")

# brandsession in name2id?
for k in name2id:
    if "brand" in k.lower() or "session" in k.lower():
        print("brand/session key:", k, name2id[k])

conn.close()
