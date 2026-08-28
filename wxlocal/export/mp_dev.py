"""导出公众号推送（订阅号消息盒 + 全部 gh_），过滤开发向语料。

数据源：decrypted/message/biz_message_0.db（PC 已同步的订阅号/服务号卡片）
说明：brandsessionholder 无独立 Msg 表，订阅号列表 = 各 gh_ 会话聚合。

用法:
  python export_mp_dev.py
  python export_mp_dev.py --fetch-bodies
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import zstd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from wxlocal.pipelines.mp_scroll.capture.body_extract import extract_body_from_html
from wxlocal.shared.http_fetch import UA, fetch_http_body
from wxlocal.shared.mp_filter import is_dev_related
from wxlocal.config.paths import MP_DEV_ARCHIVE, MP_DEV_EXPORT, MP_DEV_KB, ensure_decrypted_dir, ensure_mp_dev_dirs

_d = ensure_decrypted_dir()
BIZ_DB = _d / "message" / "biz_message_0.db"
CONTACT_DB = _d / "contact" / "contact.db"
SESSION_DB = _d / "session" / "session.db"


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
    desc_m = re.search(r"<des><!\[CDATA\[(.*?)\]\]></des>|<des>(.*?)</des>", content, re.S)
    summary = html.unescape((desc_m.group(1) or desc_m.group(2) or "").strip())[:500] if desc_m else ""
    src_m = re.search(
        r"<sourcedisplayname><!\[CDATA\[(.*?)\]\]></sourcedisplayname>|<sourcedisplayname>(.*?)</sourcedisplayname>",
        content,
        re.S,
    )
    source = html.unescape((src_m.group(1) or src_m.group(2) or "").strip()) if src_m else ""
    return {"title": title, "url": url, "summary": summary, "source_name": source}


def msg_table(username: str, tables: set[str]) -> str | None:
    t = f"Msg_{hashlib.md5(username.encode()).hexdigest()}"
    return t if t in tables else None


def load_contacts() -> dict[str, str]:
    if not CONTACT_DB.is_file():
        return {}
    import sqlite3

    conn = sqlite3.connect(CONTACT_DB)
    out = {r[0]: r[1] for r in conn.execute("SELECT username, nick_name FROM contact") if r[1]}
    conn.close()
    return out


def load_session_summaries() -> dict[str, str]:
    if not SESSION_DB.is_file():
        return {}
    import sqlite3

    conn = sqlite3.connect(SESSION_DB)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(SessionTable)")]
    out = {}
    for row in conn.execute("SELECT * FROM SessionTable"):
        d = dict(zip(cols, row))
        u = d.get("username") or ""
        if u.startswith("gh_"):
            out[u] = str(d.get("summary") or "")
    conn.close()
    return out


def export_biz_messages() -> tuple[list[dict], dict]:
    import sqlite3

    if not BIZ_DB.is_file():
        raise SystemExit(f"缺少 {BIZ_DB}，请先 watchdog.py --once 解密")

    conn = sqlite3.connect(BIZ_DB)
    tables = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
    }
    accounts = list(conn.execute("SELECT user_name, is_session FROM Name2Id"))
    contacts = load_contacts()
    session_summaries = load_session_summaries()

    raw_items: list[dict] = []
    stats = {"accounts": len(accounts), "messages_raw": 0, "session_only": 0}

    for username, is_session in accounts:
        nick = contacts.get(username, username)
        table = msg_table(username, tables)
        if table:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
            for row in conn.execute(f"SELECT * FROM [{table}] ORDER BY create_time ASC"):
                d = dict(zip(cols, row))
                content = decompress(d.get("compress_content") or d.get("message_content"))
                parsed = extract_appmsg(content)
                if not parsed or not parsed.get("title"):
                    continue
                ts = d.get("create_time") or 0
                raw_items.append(
                    {
                        "time": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "",
                        "username": username,
                        "account_name": nick,
                        "is_session": bool(is_session),
                        "source_channel": "biz_message",
                        **parsed,
                    }
                )
                stats["messages_raw"] += 1
        elif username in session_summaries:
            # Session 有摘要但 PC 未落库正文卡片
            summary = session_summaries[username]
            raw_items.append(
                {
                    "time": "",
                    "username": username,
                    "account_name": nick,
                    "is_session": bool(is_session),
                    "source_channel": "session_summary_only",
                    "title": summary[:200],
                    "url": "",
                    "summary": summary,
                    "source_name": nick,
                }
            )
            stats["session_only"] += 1

    conn.close()
    return raw_items, stats


def filter_dev_items(items: list[dict]) -> tuple[list[dict], list[dict]]:
    kept, dropped = [], []
    for i, it in enumerate(items, 1):
        ok, reason = is_dev_related(it.get("title", ""), it.get("summary", ""), it.get("account_name", ""))
        it = dict(it)
        it["filter_reason"] = reason
        it["index"] = i
        if ok:
            kept.append(it)
        else:
            dropped.append(it)
    for j, it in enumerate(kept, 1):
        it["dev_index"] = j
    return kept, dropped


def build_md(meta: dict, items: list[dict]) -> str:
    lines = [
        "# 公众号 · 开发向推送",
        "",
        f"- 导出: {meta.get('exported_at')}",
        f"- 来源: biz_message_0.db + session 摘要补全",
        f"- 原始: {meta.get('messages_raw')} 条 / 保留: {meta.get('kept')} / 丢弃: {meta.get('dropped')}",
        "",
    ]
    for it in items:
        lines += [
            f"## [{it['dev_index']}] {it['title']}",
            "",
            f"- **时间**: {it.get('time', '')}",
            f"- **公众号**: {it.get('account_name')} (`{it.get('username')}`)",
            f"- **过滤**: {it.get('filter_reason')}",
            f"- **链接**: {it.get('url', '')}",
            f"- **字数**: {len(it.get('body') or it.get('summary') or '')}",
            "",
        ]
        if it.get("summary"):
            lines += ["**摘要:**", "", it["summary"], ""]
        if it.get("body"):
            lines += ["**正文:**", "", it["body"], ""]
        lines += ["---", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="导出并过滤开发向公众号推送")
    parser.add_argument("--fetch-bodies", action="store_true", help="对保留条目抓 HTTP 正文")
    args = parser.parse_args()

    ensure_mp_dev_dirs()
    raw, stats = export_biz_messages()
    kept, dropped = filter_dev_items(raw)

    if args.fetch_bodies:
        print(f"抓取正文 {len(kept)} 条...")
        for it in kept:
            if it.get("url"):
                body = fetch_http_body(it["url"])
                if body:
                    it["body"] = body
                    it["body_source"] = "HTTP抓取"
                time.sleep(0.6)

    meta = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "source_db": str(BIZ_DB),
        "scope": "A brandsessionholder(聚合) + C all gh_ in biz_message",
        "filter": "mp_dev_filter.py",
        **stats,
        "kept": len(kept),
        "dropped": len(dropped),
        "body_fetched": sum(1 for i in kept if i.get("body")),
    }

    stamp = datetime.now().strftime("%Y-%m-%d")
    batch = MP_DEV_ARCHIVE / f"{stamp}-dev"
    batch.mkdir(parents=True, exist_ok=True)

    payload = {"meta": meta, "items": kept, "dropped_sample": dropped[:30]}
    out_json = batch / "mp_dev.json"
    out_md = batch / "mp_dev.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(build_md(meta, kept), encoding="utf-8")

    # 最新快照
    latest_json = MP_DEV_EXPORT / "mp_dev_latest.json"
    latest_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (MP_DEV_KB / "INDEX.md").write_text(
        "\n".join(
            [
                "# 公众号 · 开发向语料",
                "",
                f"- 最近导出: `{meta['exported_at']}`",
                f"- 保留 **{meta['kept']}** / 原始 {meta['messages_raw']}",
                f"- 批次: [`archive/{batch.name}/`](archive/{batch.name}/)",
                f"- 快照: [`exports/mp_dev_latest.json`](exports/mp_dev_latest.json)",
                "",
                "过滤规则见知识库 `wechat/mp-scroll/config/dev_filter.json`（wxlocal 读取）。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"raw={stats['messages_raw']} kept={len(kept)} dropped={len(dropped)} session_only={stats['session_only']}")
    print(f"JSON: {out_json}")
    print(f"MD:   {out_md}")
    print("\n--- 开发向保留 ---")
    for it in kept[:15]:
        print(f"  [{it['dev_index']}] {it['title'][:55]} | {it['account_name']}")
    if len(kept) > 15:
        print(f"  ... +{len(kept)-15}")


if __name__ == "__main__":
    main()
