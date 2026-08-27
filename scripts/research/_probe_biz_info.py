"""探测 biz_info / general 里未关注公众号元数据。"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def dump_schema(conn, table: str, limit: int = 3) -> None:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info([{table}])")]
    print(f"\n[{table}] cols={cols}")
    for row in conn.execute(f"SELECT * FROM [{table}] LIMIT {limit}"):
        d = dict(zip(cols, row))
        for k, v in d.items():
            if v is None:
                continue
            s = v.decode("utf-8", errors="replace") if isinstance(v, bytes) else str(v)
            if len(s) > 200:
                s = s[:200] + "..."
            print(f"  {k}: {s}")


def main() -> None:
    contact = sqlite3.connect(ROOT / "decrypted/contact/contact.db")
    general = sqlite3.connect(ROOT / "decrypted/general/general.db")

    print("=== contact.biz_info ===")
    n = contact.execute("SELECT COUNT(*) FROM biz_info").fetchone()[0]
    print("rows:", n)
    dump_schema(contact, "biz_info", 2)

    # search nick in biz_info
    cols = [r[1] for r in contact.execute("PRAGMA table_info(biz_info)")]
    text_cols = cols
    for col in text_cols:
        try:
            rows = contact.execute(
                f"SELECT * FROM biz_info WHERE CAST([{col}] AS TEXT) LIKE '%笔记%' OR CAST([{col}] AS TEXT) LIKE '%大叔%' LIMIT 5"
            ).fetchall()
            if rows:
                print(f"\nbiz_info hits in {col}:")
                for row in rows:
                    print(dict(zip(cols, row)))
        except Exception:
            pass

    print("\n=== general.db ===")
    for t in ["WeAppBizAttrSyncBufferTableV02", "biz_subscribe_status", "brand_search_record"]:
        try:
            n = general.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            print(f"{t}: {n}")
            if n:
                dump_schema(general, t, 2)
        except Exception as e:
            print(f"{t}: {e}")

    # compare biz_info usernames vs contact gh_
    biz_usernames = {r[0] for r in contact.execute("SELECT username FROM biz_info")}
    gh_contacts = {r[0] for r in contact.execute("SELECT username FROM contact WHERE username LIKE 'gh_%'")}
    only_biz = biz_usernames - gh_contacts
    print(f"\nbiz_info usernames: {len(biz_usernames)}")
    print(f"gh_ contacts: {len(gh_contacts)}")
    print(f"in biz_info but NOT gh_ contact: {len(only_biz)}")
    if only_biz:
        sample = list(only_biz)[:10]
        for u in sample:
            row = contact.execute("SELECT * FROM biz_info WHERE username=?", (u,)).fetchone()
            print(f"  orphan biz_info: {u} -> {row}")

    contact.close()
    general.close()


if __name__ == "__main__":
    main()
