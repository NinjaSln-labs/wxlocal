"""探测 weclaw / message_resource / biz kvdb。"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
from wxlocal.config.config import DATA_ROOT

RAW_KVDB = Path(DATA_ROOT) / "<account>" / "db_storage" / "message" / "biz_message_0.kvdb" if DATA_ROOT else Path("biz_message_0.kvdb")
KEYWORDS = ["大叔笔记", "大叔", "dashu", "笔记"]


def probe_sqlite(path: Path) -> None:
    if not path.is_file():
        print(f"missing {path}")
        return
    print(f"\n=== {path.name} ({path.stat().st_size} bytes) ===")
    try:
        conn = sqlite3.connect(path)
    except Exception as e:
        print(f"  not sqlite: {e}")
        raw = path.read_bytes()
        for kw in KEYWORDS:
            if kw.encode("utf-8") in raw:
                print(f"  binary hit: {kw}")
        return
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print(f"  tables: {tables}")
    for t in tables:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            print(f"    {t}: {n}")
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info([{t}])")]
            for col in cols:
                try:
                    for row in conn.execute(f"SELECT [{col}] FROM [{t}] LIMIT 1000"):
                        val = row[0]
                        if val is None:
                            continue
                        s = val.decode("utf-8", errors="replace") if isinstance(val, bytes) else str(val)
                        if any(k in s for k in KEYWORDS):
                            print(f"      HIT {t}.{col}: {s[:120]}")
                except Exception:
                    pass
        except Exception as e:
            print(f"    {t}: err {e}")
    conn.close()


def main() -> None:
    for name in ["weclaw.db", "message_resource.db"]:
        probe_sqlite(ROOT / "decrypted/message" / name)
    probe_sqlite(RAW_KVDB)


if __name__ == "__main__":
    main()
