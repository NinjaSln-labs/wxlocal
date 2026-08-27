"""biz_info 里所有公众号名 + 与 contact 差集。"""
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def safe_str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return str(v)


def main() -> None:
    contact = sqlite3.connect(ROOT / "decrypted/contact/contact.db")
    contact.text_factory = bytes

    cols = [safe_str(r[1]) for r in contact.execute("PRAGMA table_info(biz_info)")]
    rows = contact.execute("SELECT * FROM biz_info").fetchall()

    gh_contact = {
        safe_str(r[0]): safe_str(r[1])
        for r in contact.execute("SELECT username, nick_name FROM contact WHERE username LIKE 'gh_%'")
    }

    names = []
    for row in rows:
        d = {cols[i]: row[i] for i in range(len(cols))}
        u = safe_str(d.get("username"))
        brand = safe_str(d.get("brand_info"))
        ext = safe_str(d.get("external_info"))
        blist = safe_str(d.get("brand_list"))
        nick = gh_contact.get(u, "")
        # try extract display name from brand_info xml/json
        nick_guess = nick
        for pat in [
            r"<nickname><!\[CDATA\[(.*?)\]\]></nickname>",
            r'"nick_name"\s*:\s*"([^"]+)"',
            r"display_name[=:]\\x00?([^\\x00]+)",
        ]:
            m = re.search(pat, brand + ext + blist)
            if m:
                nick_guess = m.group(1)
                break
        names.append((u, nick_guess or nick or u, u in gh_contact))

    print(f"biz_info total: {len(names)}")
    followed = [x for x in names if x[2]]
    unfollowed = [x for x in names if not x[2]]
    print(f"  matched gh_ contact: {len(followed)}")
    print(f"  NOT in contact: {len(unfollowed)}")

    hits = [x for x in names if "大叔" in x[1] or "笔记" in x[1]]
    print(f"\nkeyword hits in biz_info names: {len(hits)}")
    for x in hits:
        print(f"  {x[0]} | {x[1]} | in_contact={x[2]}")

    print("\n--- sample NOT in contact (first 20) ---")
    for u, nick, _ in unfollowed[:20]:
        print(f"  {nick} ({u})")

    # dump one brand_info sample for gh account
    sample = contact.execute(
        "SELECT username, brand_info FROM biz_info WHERE username LIKE 'gh_%' LIMIT 1"
    ).fetchone()
    if sample:
        print("\n--- brand_info sample ---")
        print(safe_str(sample[0]), safe_str(sample[1])[:500])

    contact.close()


if __name__ == "__main__":
    main()
