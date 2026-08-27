"""列出 biz_message 近期新增/全部消息，及 contact 新增 gh_。"""
from __future__ import annotations

import hashlib
import html
import re
import sqlite3
import zstd
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIZ_DB = ROOT / "decrypted/message/biz_message_0.db"
CONTACT_DB = ROOT / "decrypted/contact/contact.db"
SESSION_DB = ROOT / "decrypted/session/session.db"

# 上次探测基准（用户打开大叔笔记后）
BASELINE_MSG_COUNT = 82
BASELINE_GH_CONTACTS = 184
BASELINE_BIZ_ACCOUNTS = 50


def decompress(data) -> str:
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


def extract_appmsg(content: str) -> dict | None:
    if not content or "<appmsg" not in content and "<title" not in content:
        return None
    title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", content, re.S)
    if not title_m:
        return None
    title = html.unescape((title_m.group(1) or title_m.group(2) or "").strip())
    url_m = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>|<url>(.*?)</url>", content, re.S)
    url = html.unescape((url_m.group(1) or url_m.group(2) or "").strip()) if url_m else ""
    src_m = re.search(
        r"<sourcedisplayname><!\[CDATA\[(.*?)\]\]></sourcedisplayname>",
        content,
        re.S,
    )
    source = html.unescape(src_m.group(1).strip()) if src_m else ""
    return {"title": title, "url": url, "source_name": source}


def msg_table(username: str, tables: set[str]) -> str | None:
    t = f"Msg_{hashlib.md5(username.encode()).hexdigest()}"
    return t if t in tables else None


def main() -> None:
    contact = sqlite3.connect(CONTACT_DB)
    session = sqlite3.connect(SESSION_DB)
    biz = sqlite3.connect(BIZ_DB)

    gh_contacts = {
        r[0]: r[1]
        for r in contact.execute("SELECT username, nick_name FROM contact WHERE username LIKE 'gh_%'")
    }
    tables = {
        r[0]
        for r in biz.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
    }
    accounts = list(biz.execute("SELECT user_name, is_session FROM Name2Id"))

    items: list[dict] = []
    for username, is_session in accounts:
        nick = gh_contacts.get(username, username)
        table = msg_table(username, tables)
        if not table:
            continue
        cols = [r[1] for r in biz.execute(f"PRAGMA table_info({table})")]
        for row in biz.execute(f"SELECT * FROM [{table}]"):
            d = dict(zip(cols, row))
            parsed = extract_appmsg(decompress(d.get("compress_content") or d.get("message_content")))
            if not parsed or not parsed.get("title"):
                continue
            ts = d.get("create_time") or 0
            items.append(
                {
                    "time": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "",
                    "ts": ts,
                    "username": username,
                    "account_name": nick,
                    **parsed,
                }
            )

    items.sort(key=lambda x: x["ts"], reverse=True)

    print("=== 体量 ===")
    print(f"biz_message 消息: {len(items)} (基准 {BASELINE_MSG_COUNT}, Δ{len(items)-BASELINE_MSG_COUNT})")
    print(f"biz Name2Id: {len(accounts)} (基准 {BASELINE_BIZ_ACCOUNTS})")
    print(f"contact gh_: {len(gh_contacts)} (基准 {BASELINE_GH_CONTACTS}, Δ{len(gh_contacts)-BASELINE_GH_CONTACTS})")

    # contact 有、biz 无 Msg 的号（点开推荐号常见）
    biz_users = {u for u, _ in accounts}
    opened_only = []
    for u, nick in gh_contacts.items():
        t = msg_table(u, tables)
        if u not in biz_users or not t:
            opened_only.append((u, nick, "no_name2id" if u not in biz_users else "no_msg_table"))
        elif biz.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0] == 0:
            opened_only.append((u, nick, "empty_msg_table"))

    print(f"\ncontact 有记录但 biz 无消息: {len(opened_only)}")
    for u, nick, why in opened_only[:20]:
        print(f"  [{why}] {nick} ({u})")

    # 今天 12:00 以后的消息（用户刚打开的）
    cutoff = datetime(2026, 8, 27, 12, 0, 0).timestamp()
    recent = [i for i in items if i["ts"] >= cutoff]
    print(f"\n=== 12:00 之后写入 biz_message: {len(recent)} ===")
    for i in recent:
        print(f"  [{i['time']}] {i['account_name']} | {i['title'][:70]}")

    print(f"\n=== 最近 15 条 biz_message ===")
    for i in items[:15]:
        url_ok = "mp.weixin.qq.com" in (i.get("url") or "")
        print(f"  [{i['time']}] {i['account_name']} | {i['title'][:65]} | url={'Y' if url_ok else 'N'}")

    # brandsessionholder
    cols = [r[1] for r in session.execute("PRAGMA table_info(SessionTable)")]
    for row in session.execute("SELECT * FROM SessionTable WHERE username='brandsessionholder'"):
        d = dict(zip(cols, row))
        print(f"\nbrandsessionholder summary: {str(d.get('summary') or '')[:120]}")
        ts = d.get("last_timestamp")
        if ts:
            print(f"  last_timestamp: {datetime.fromtimestamp(ts)}")

    contact.close()
    session.close()
    biz.close()


if __name__ == "__main__":
    main()
