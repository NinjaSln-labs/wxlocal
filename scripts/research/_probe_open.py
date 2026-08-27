"""Check biz_message and webview profile after opening articles."""
from __future__ import annotations

import html
import re
import sqlite3
import zstd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIZ = ROOT / "decrypted/message/biz_message_0.db"
PROFILES = __import__("paths").default_radium_profiles()

URL_RE = re.compile(r"https?://mp\.weixin\.qq\.com/s[^\s\"'\\<>]{10,400}")


def dec(data) -> str:
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


def scan_biz() -> None:
    print("=== biz_message recent ===")
    if not BIZ.is_file():
        print("  missing", BIZ)
        return
    conn = sqlite3.connect(BIZ)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    recent = []
    for t in sorted(tables):
        if not t.startswith("Msg_"):
            continue
        try:
            rows = conn.execute(
                f'SELECT sort_seq, message_content FROM "{t}" ORDER BY sort_seq DESC LIMIT 8'
            ).fetchall()
        except sqlite3.Error:
            continue
        for sort_seq, content in rows:
            text = dec(content)
            if "mp.weixin.qq.com" not in text and "<title>" not in text:
                continue
            m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", text, re.S)
            title = html.unescape((m.group(1) or m.group(2) or "").strip()) if m else ""
            recent.append((sort_seq, title, t))
    recent.sort(reverse=True)
    print(f"  cards={len(recent)}")
    for sort_seq, title, t in recent[:15]:
        print(f"  {sort_seq} {title[:70] or '(no title)'} {t}")
    conn.close()


def scan_profile(name: str) -> None:
    print(f"\n=== profile {name} ===")
    for idb_name in (
        "https_mp.weixin.qq.com_0.indexeddb.leveldb",
        "weixin_xworker_0.indexeddb.leveldb",
    ):
        for idb in PROFILES.glob(f"{name}/IndexedDB/{idb_name}"):
            blob = b"".join(
                f.read_bytes() for f in idb.iterdir() if f.suffix in (".log", ".ldb") and f.is_file()
            )
            urls = sorted(set(URL_RE.findall(blob.decode("utf-8", errors="replace"))))
            newest = max(idb.iterdir(), key=lambda f: f.stat().st_mtime)
            print(f"  {idb.name}: urls={len(urls)} newest={newest.name} mtime={newest.stat().st_mtime}")


def main() -> None:
    scan_biz()
    for prof in ("multitab_29adb3f5d489db767b94e00abb4cc4e4", "webview_29adb3f5d489db767b94e00abb4cc4e4"):
        scan_profile(prof)

    # very recent biz cards
    if BIZ.is_file():
        from datetime import datetime

        conn = sqlite3.connect(BIZ)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")]
        rows = []
        for t in tables:
            try:
                batch = conn.execute(
                    f'SELECT sort_seq, message_content FROM "{t}" ORDER BY sort_seq DESC LIMIT 2'
                ).fetchall()
            except sqlite3.Error:
                continue
            for sort_seq, content in batch:
                text = dec(content)
                if "<title>" not in text:
                    continue
                m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", text, re.S)
                title = html.unescape((m.group(1) or m.group(2) or "").strip()) if m else ""
                um = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>|<url>(.*?)</url>", text, re.S)
                url = html.unescape((um.group(1) or um.group(2) or "").strip()) if um else ""
                rows.append((sort_seq, title, url))
        conn.close()
        rows.sort(reverse=True)
        print("\n=== biz_message top 8 (with time) ===")
        for sort_seq, title, url in rows[:8]:
            ts = datetime.fromtimestamp(sort_seq / 1000).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {ts} {title[:65]}")
            if url:
                print(f"    {url[:90]}")


if __name__ == "__main__":
    main()
