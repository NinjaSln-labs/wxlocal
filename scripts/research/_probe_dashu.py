"""查找「大叔笔记」及未关注推荐号在 DB 中的位置。"""
import hashlib
import re
import sqlite3
import zstd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEYWORDS = ["大叔", "笔记", "dashu"]


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


def msg_table(username: str, tables: set[str]) -> str | None:
    t = f"Msg_{hashlib.md5(username.encode()).hexdigest()}"
    return t if t in tables else None


def search_text(label: str, text: str, extra: str = "") -> None:
    if any(k in text for k in KEYWORDS):
        print(f"[{label}] {extra} :: {text[:120]}")


def main() -> None:
    contact = sqlite3.connect(ROOT / "decrypted/contact/contact.db")
    session = sqlite3.connect(ROOT / "decrypted/session/session.db")
    biz = sqlite3.connect(ROOT / "decrypted/message/biz_message_0.db")

    print("=== contact.db ===")
    for u, nick in contact.execute("SELECT username, nick_name FROM contact"):
        search_text("contact", (nick or "") + u, u)

    print("\n=== session.db (all non-gh special + keyword hits) ===")
    cols = [r[1] for r in session.execute("PRAGMA table_info(SessionTable)")]
    all_sessions = []
    for row in session.execute("SELECT * FROM SessionTable"):
        d = dict(zip(cols, row))
        all_sessions.append(d)
        u = d.get("username") or ""
        summ = str(d.get("summary") or "")
        nick = str(d.get("nick_name") or d.get("nickname") or "")
        if any(k in summ + nick + u for k in KEYWORDS):
            print(f"  hit: {u} | nick={nick} | summary={summ[:100]}")
        if u in ("brandsessionholder", "brandservicesessionholder", "newsapp"):
            print(f"  special: {u} | summary={summ[:150]}")

    print(f"\n  total sessions: {len(all_sessions)}")
    gh_sess = [d for d in all_sessions if (d.get("username") or "").startswith("gh_")]
    print(f"  gh_ sessions: {len(gh_sess)}")

    print("\n=== biz_message Name2Id (non-gh) ===")
    biz_tables = {
        r[0]
        for r in biz.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
    }
    accounts = list(biz.execute("SELECT user_name, is_session FROM Name2Id"))
    contacts = {r[0]: r[1] for r in contact.execute("SELECT username, nick_name FROM contact")}

    for u, is_sess in accounts:
        if not u.startswith("gh_"):
            nick = contacts.get(u, "")
            print(f"  {u} is_session={is_sess} nick={nick}")

    print("\n=== biz_message full text scan (keyword) ===")
    hits = []
    for u, is_sess in accounts:
        t = msg_table(u, biz_tables)
        if not t:
            continue
        cols_m = [r[1] for r in biz.execute(f"PRAGMA table_info({t})")]
        for row in biz.execute(f"SELECT * FROM [{t}]"):
            d = dict(zip(cols_m, row))
            content = decompress(d.get("compress_content") or d.get("message_content"))
            if any(k in content for k in KEYWORDS):
                title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", content, re.S)
                title = title_m.group(1) if title_m else content[:80]
                hits.append((u, contacts.get(u, u), title[:80], d.get("create_time")))
    print(f"  keyword hits in biz: {len(hits)}")
    for h in hits[:10]:
        print(f"    {h}")

    print("\n=== biz_message: sourcedisplayname scan ===")
    names = set()
    for u, _ in accounts:
        t = msg_table(u, biz_tables)
        if not t:
            continue
        cols_m = [r[1] for r in biz.execute(f"PRAGMA table_info({t})")]
        for row in biz.execute(f"SELECT * FROM [{t}] LIMIT 200"):
            d = dict(zip(cols_m, row))
            content = decompress(d.get("compress_content") or d.get("message_content"))
            m = re.search(
                r"<sourcedisplayname><!\[CDATA\[(.*?)\]\]></sourcedisplayname>",
                content,
                re.S,
            )
            if m:
                names.add(m.group(1))
    dashu_names = [n for n in sorted(names) if "大叔" in n or "笔记" in n]
    print(f"  unique sourcedisplayname count: {len(names)}")
    print(f"  dashu-like names: {dashu_names}")
    if names:
        print("  sample names:", list(sorted(names))[:20])

    # gh in biz but NOT in contact
    print("\n=== biz gh_ NOT in contact.db ===")
    contact_set = {r[0] for r in contact.execute("SELECT username FROM contact")}
    orphan = []
    for u, _ in accounts:
        if u.startswith("gh_") and u not in contact_set:
            t = msg_table(u, biz_tables)
            cnt = biz.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0] if t else 0
            orphan.append((u, cnt))
    print(f"  count: {len(orphan)}")
    for u, cnt in orphan[:15]:
        print(f"    {u} msgs={cnt}")

    contact.close()
    session.close()
    biz.close()


if __name__ == "__main__":
    main()
