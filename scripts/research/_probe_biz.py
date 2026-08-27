"""探测 biz_message_0.db 结构。"""
import sqlite3
from pathlib import Path

db = Path("decrypted/message/biz_message_0.db")
conn = sqlite3.connect(db)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("tables:", tables)
for t in tables:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
    try:
        n = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    except Exception as e:
        n = f"err:{e}"
    print(f"\n{t} rows={n}")
    print(" cols:", cols)
    if isinstance(n, int) and n > 0:
        row = conn.execute(f"SELECT * FROM [{t}] LIMIT 1").fetchone()
        print(" sample keys len", len(row))
        for i, c in enumerate(cols[:15]):
            v = row[i]
            if isinstance(v, bytes):
                v = v[:80]
            print(f"  {c}: {str(v)[:120]}")

conn.close()
