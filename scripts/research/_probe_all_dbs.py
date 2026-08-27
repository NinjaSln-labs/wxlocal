"""全库搜索关键词 + 列出 biz/session 以外可疑表。"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "decrypted"
KEYWORDS = ["大叔笔记", "大叔", "dashu"]


def scan_db(path: Path) -> None:
    try:
        conn = sqlite3.connect(path)
    except Exception as e:
        print(f"SKIP {path}: {e}")
        return
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    hits = []
    for t in tables:
        try:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info([{t}])")]
        except Exception:
            continue
        text_cols = [c for c in cols if any(x in c.lower() for x in ("content", "summary", "title", "name", "nick", "data", "xml", "msg", "text", "desc"))]
        if not text_cols:
            text_cols = cols[:8]
        for col in text_cols:
            try:
                for row in conn.execute(f"SELECT [{col}] FROM [{t}] LIMIT 5000"):
                    val = row[0]
                    if val is None:
                        continue
                    if isinstance(val, bytes):
                        try:
                            s = val.decode("utf-8", errors="replace")
                        except Exception:
                            s = repr(val[:80])
                    else:
                        s = str(val)
                    if any(k in s for k in KEYWORDS):
                        hits.append((t, col, s[:150]))
            except Exception:
                pass
    if hits:
        print(f"\n=== HIT {path.relative_to(ROOT.parent)} ({len(hits)} rows) ===")
        for h in hits[:20]:
            print(f"  {h[0]}.{h[1]}: {h[2]}")
    conn.close()


def list_interesting_tables(path: Path) -> None:
    try:
        conn = sqlite3.connect(path)
    except Exception:
        return
    rel = path.relative_to(ROOT.parent)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    interesting = [t for t in tables if any(x in t.lower() for x in ("brand", "biz", "feed", "subscr", "mp", "article", "timeline", "recommend", "session", "holder"))]
    if interesting:
        print(f"\n--- {rel} interesting tables ---")
        for t in interesting:
            try:
                n = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            except Exception:
                n = "?"
            print(f"  {t}: {n}")
    conn.close()


def main() -> None:
    dbs = sorted(ROOT.rglob("*.db"))
    print(f"scanning {len(dbs)} db files...")
    for db in dbs:
        list_interesting_tables(db)
        scan_db(db)


if __name__ == "__main__":
    main()
