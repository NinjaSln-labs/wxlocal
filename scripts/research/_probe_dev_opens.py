"""搜今日 biz_message + session + contact 中 AI/开发向新增。"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import zstd
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEV_KW = [
    "ai", "gpt", "claude", "cursor", "agent", "llm", "大模型", "开源", "github",
    "代码", "编程", "开发", "程序员", "架构", "模型", "推理", "api", "sdk",
    "copilot", "codex", "skill", "mcp", "vibe", "deepseek", "rag", "微调",
]

# 用户说「都不是」的三篇（误匹配背景推送）
NOISE = [
    "开门杀",
    "石斛",
    "网约车司机获刑",
]


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


def is_dev(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in DEV_KW)


def is_noise(title: str) -> bool:
    return any(n in title for n in NOISE)


def extract(content: str) -> dict | None:
    title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", content, re.S)
    if not title_m:
        return None
    title = html.unescape(title_m.group(1).strip())
    url_m = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>", content, re.S)
    url = html.unescape(url_m.group(1).strip()) if url_m else ""
    return {"title": title, "url": url}


def main() -> None:
    contact = sqlite3.connect(ROOT / "decrypted/contact/contact.db")
    session = sqlite3.connect(ROOT / "decrypted/session/session.db")
    biz = sqlite3.connect(ROOT / "decrypted/message/biz_message_0.db")

    contacts = {r[0]: r[1] for r in contact.execute("SELECT username, nick_name FROM contact")}
    tables = {
        r[0]
        for r in biz.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
    }
    accounts = list(biz.execute("SELECT user_name, is_session FROM Name2Id"))

    all_items = []
    for u, _ in accounts:
        t = f"Msg_{hashlib.md5(u.encode()).hexdigest()}"
        if t not in tables:
            continue
        cols = [r[1] for r in biz.execute(f"PRAGMA table_info({t})")]
        for row in biz.execute(f"SELECT * FROM [{t}]"):
            d = dict(zip(cols, row))
            parsed = extract(decompress(d.get("compress_content") or d.get("message_content")))
            if not parsed:
                continue
            ts = d.get("create_time") or 0
            all_items.append(
                {
                    "ts": ts,
                    "time": datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "",
                    "account": contacts.get(u, u),
                    "username": u,
                    **parsed,
                }
            )

    all_items.sort(key=lambda x: x["ts"], reverse=True)
    cutoff = datetime(2026, 8, 27, 11, 35, 0).timestamp()
    recent = [i for i in all_items if i["ts"] >= cutoff]
    recent_dev = [i for i in recent if is_dev(i["title"]) and not is_noise(i["title"])]

    print("=== 体量 ===")
    print(f"biz_message 总消息: {len(all_items)}")
    print(f"11:35 后全部: {len(recent)}")
    print(f"11:35 后 AI/开发向: {len(recent_dev)}")

    print("\n=== 11:35 后【全部】落库 ===")
    for i in recent:
        dev = "DEV" if is_dev(i["title"]) else "   "
        print(f"  [{dev}] {i['time']} | {i['account']} | {i['title'][:70]}")

    print("\n=== 11:35 后【AI/开发向】落库 ===")
    if not recent_dev:
        print("  （无）")
    for i in recent_dev:
        print(f"  [{i['time']}] {i['account']} | {i['title'][:70]}")
        print(f"       {i['url'][:90]}")

    # session gh_ 摘要里 dev 向
    cols = [r[1] for r in session.execute("PRAGMA table_info(SessionTable)")]
    print("\n=== session 摘要含 AI/开发关键词 ===")
    for row in session.execute("SELECT * FROM SessionTable"):
        d = dict(zip(cols, row))
        summ = str(d.get("summary") or "")
        u = d.get("username") or ""
        if is_dev(summ):
            nick = contacts.get(u, u)
            print(f"  {nick or u}: {summ[:100]}")

    # contact 新增 ghost（有 contact 无 biz 消息）里 dev 向号名
    biz_users = {u for u, _ in accounts}
    print("\n=== contact 有 / biz 无消息 · 号名像技术号 ===")
    for u, nick in contact.execute(
        "SELECT username, nick_name FROM contact WHERE username LIKE 'gh_%'"
    ):
        if u in biz_users:
            continue
        blob = (nick or "") + u
        if is_dev(blob):
            print(f"  {nick} ({u})")

    # 和早上首导出口对比
    first = ROOT / "output" / "biz_first_export_urls.json"
    if not first.is_file():
        urls_morning = set()
        snap_path = ROOT / "output" / "biz_snapshot.json"
        if snap_path.is_file():
            # 用 11:38 前逻辑：读 archive 或建 baseline
            pass
    else:
        urls_morning = set(json.loads(first.read_text(encoding="utf-8")))

    contact.close()
    session.close()
    biz.close()


if __name__ == "__main__":
    main()
