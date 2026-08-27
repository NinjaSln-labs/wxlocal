"""大叔笔记 gh_0e4c15b328bc 落库探测。"""
import hashlib
import re
import sqlite3
import zstd
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GH = "gh_0e4c15b328bc"


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


def msg_table(u: str, tables: set[str]) -> str | None:
    t = f"Msg_{hashlib.md5(u.encode()).hexdigest()}"
    return t if t in tables else None


def main() -> None:
    contact = sqlite3.connect(ROOT / "decrypted/contact/contact.db")
    session = sqlite3.connect(ROOT / "decrypted/session/session.db")
    biz = sqlite3.connect(ROOT / "decrypted/message/biz_message_0.db")

    nick = contact.execute("SELECT nick_name FROM contact WHERE username=?", (GH,)).fetchone()
    print("contact:", GH, nick)

    in_biz = biz.execute("SELECT user_name, is_session FROM Name2Id WHERE user_name=?", (GH,)).fetchone()
    print("biz Name2Id:", in_biz)

    cols = [r[1] for r in session.execute("PRAGMA table_info(SessionTable)")]
    for row in session.execute("SELECT * FROM SessionTable"):
        d = dict(zip(cols, row))
        if d.get("username") in (GH, "brandsessionholder"):
            print("\nsession", d.get("username"))
            for k, v in d.items():
                if v not in (None, "", 0):
                    print(f"  {k}: {v}")

    tables = {r[0] for r in biz.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")}
    t = msg_table(GH, tables)
    print("\nMsg table:", t)
    if t:
        n = biz.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        print("msg count:", n)
        cols_m = [r[1] for r in biz.execute(f"PRAGMA table_info({t})")]
        for row in biz.execute(f"SELECT * FROM [{t}] ORDER BY create_time DESC LIMIT 3"):
            d = dict(zip(cols_m, row))
            content = decompress(d.get("compress_content") or d.get("message_content"))
            ts = d.get("create_time")
            print("\n--- message ---")
            print("time:", datetime.fromtimestamp(ts) if ts else "")
            url_m = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>", content, re.S)
            title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", content, re.S)
            print("title:", title_m.group(1) if title_m else content[:200])
            print("url:", url_m.group(1) if url_m else "")

    # brandsessionholder table?
    bh = msg_table("brandsessionholder", tables)
    print("\nbrandsessionholder table:", bh, "exists=", bh is not None)
    if bh:
        print("count:", biz.execute(f"SELECT COUNT(*) FROM [{bh}]").fetchone()[0])

    row = contact.execute(
        "SELECT username, nick_name FROM contact WHERE username=?", (GH,)
    ).fetchone()
    print("\ncontact detail:", row)
    bi = contact.execute(
        "SELECT brand_info, external_info, home_url FROM biz_info WHERE username=?", (GH,)
    ).fetchone()
    print("biz_info:", "yes" if bi else "no")
    if bi:
        for i, x in enumerate(bi):
            s = x.decode("utf-8", errors="replace") if isinstance(x, bytes) else str(x)
            print(f"  [{i}]: {s[:500]}")

    key = "110%"
    print("\nscan biz for article title fragment...")
    for t in tables:
        cols_m = [r[1] for r in biz.execute(f"PRAGMA table_info({t})")]
        for row in biz.execute(f"SELECT * FROM [{t}]"):
            d = dict(zip(cols_m, row))
            content = decompress(d.get("compress_content") or d.get("message_content"))
            if key in content or "大叔笔记" in content:
                print("HIT", t)
                url_m = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>", content, re.S)
                title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", content, re.S)
                print(" title:", title_m.group(1) if title_m else "")
                print(" url:", url_m.group(1) if url_m else "")

    contact.close()
    session.close()
    biz.close()


if __name__ == "__main__":
    main()
