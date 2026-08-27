"""对比 Name2Id 新增账号 + 今日 11:00 后所有 biz 消息。"""
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# 保存快照供下次对比
SNAP = ROOT / "output" / "biz_snapshot.json"


def load_items():
    import html
    import re
    import zstd

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

    contact = sqlite3.connect(ROOT / "decrypted/contact/contact.db")
    biz = sqlite3.connect(ROOT / "decrypted/message/biz_message_0.db")
    contacts = {r[0]: r[1] for r in contact.execute("SELECT username, nick_name FROM contact")}
    tables = {
        r[0]
        for r in biz.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
    }
    accounts = list(biz.execute("SELECT user_name, is_session FROM Name2Id"))
    items = []
    for u, _ in accounts:
        t = f"Msg_{hashlib.md5(u.encode()).hexdigest()}"
        if t not in tables:
            continue
        cols = [r[1] for r in biz.execute(f"PRAGMA table_info({t})")]
        for row in biz.execute(f"SELECT * FROM [{t}]"):
            d = dict(zip(cols, row))
            content = decompress(d.get("compress_content") or d.get("message_content"))
            m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", content, re.S)
            if not m:
                continue
            title = html.unescape(m.group(1).strip())
            url_m = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>", content, re.S)
            url = html.unescape(url_m.group(1).strip()) if url_m else ""
            ts = d.get("create_time") or 0
            items.append(
                {
                    "time": datetime.fromtimestamp(ts).isoformat(sep=" ", timespec="seconds") if ts else "",
                    "ts": ts,
                    "username": u,
                    "account": contacts.get(u, u),
                    "title": title,
                    "url": url,
                }
            )
    contact.close()
    biz.close()
    return accounts, items


def main():
    accounts, items = load_items()
    items.sort(key=lambda x: x["ts"], reverse=True)
    cutoff = datetime(2026, 8, 27, 11, 0, 0).timestamp()
    since11 = [i for i in items if i["ts"] >= cutoff]

    prev = {}
    if SNAP.is_file():
        prev = json.loads(SNAP.read_text(encoding="utf-8"))

    prev_urls = {x["url"] for x in prev.get("items", []) if x.get("url")}
    prev_titles = {x["title"] for x in prev.get("items", [])}
    new_items = [i for i in items if i["url"] and i["url"] not in prev_urls]
    if not prev:
        new_items = since11

    print(f"总消息: {len(items)} | Name2Id: {len(accounts)}")
    print(f"今日 11:00 后: {len(since11)}")
    print(f"相对上次快照新增(按 URL): {len(new_items)}")

    print("\n--- 今日 11:00 后 ---")
    for i in since11:
        print(f"  [{i['time']}] {i['account']} | {i['title'][:72]}")

    if new_items:
        print("\n--- 相对快照新增 ---")
        for i in sorted(new_items, key=lambda x: x["ts"], reverse=True):
            print(f"  [{i['time']}] {i['account']} | {i['title'][:72]}")

    # gh_ 在 contact 但不在 Name2Id（点开未落消息）
    contact = sqlite3.connect(ROOT / "decrypted/contact/contact.db")
    biz = sqlite3.connect(ROOT / "decrypted/message/biz_message_0.db")
    biz_users = {r[0] for r in biz.execute("SELECT user_name FROM Name2Id")}
    ghost = []
    for u, nick in contact.execute("SELECT username, nick_name FROM contact WHERE username LIKE 'gh_%'"):
        if u not in biz_users:
            ghost.append((u, nick))
    print(f"\ncontact 有 / biz 无 Name2Id 的 gh_: {len(ghost)}")
    # 可能是本次点开产生的：大叔笔记等
    for u, nick in ghost:
        if "笔记" in (nick or "") or nick in ("大叔笔记",):
            print(f"  * {nick} ({u})")

    snap = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "count": len(items),
        "items": items,
        "name2id": [a[0] for a in accounts],
    }
    SNAP.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
