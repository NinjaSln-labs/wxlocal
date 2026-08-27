"""Compare full vs triple URL characteristics in IDB backup."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from mp_capture.idb_reader import TRIPLEKEY_RE, read_storage_bytes, url_has_sn

BACKUP = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)
NICK_RE = re.compile(
    rb'"(?:nick_name|nickname|source_display_name)"\s*:\s*"((?:\\.|[^"\\]){2,120})"'
)
URL_RE = re.compile(
    rb"https?://mp\.weixin\.qq\.com/s(?:/[A-Za-z0-9_\-]{8,40}|[\?/][^\s\"'\\<>]{10,400})"
)


def window(text: bytes, pos: int, before: int = 600, after: int = 600) -> bytes:
    return text[max(0, pos - before) : pos + after]


def main() -> None:
    blob = read_storage_bytes([BACKUP])
    text = blob.decode("utf-8", "replace")

    full_nicks: list[str] = []
    triple_nicks: list[str] = []

    for m in URL_RE.finditer(blob):
        url = m.group(0).decode("utf-8", "replace")
        w = window(blob, m.start()).decode("utf-8", "replace")
        nicks = NICK_RE.findall(window(blob, m.start()))
        nick = nicks[0].decode("utf-8", "replace") if nicks else ""
        if url_has_sn(url):
            full_nicks.append(nick)
        elif "__biz=" in url:
            triple_nicks.append(nick)

    triples = TRIPLEKEY_RE.findall(text)
    print(f"blob={len(blob)} full_urls={len(full_nicks)} triple_urls={len(triple_nicks)} triplekeys={len(triples)}")

    print("\nFULL URL sample nicks (top 10):")
    for n, c in Counter(full_nicks).most_common(10):
        print(f"  {c:3d}  {n or '(empty)'}")

    print("\nTRIPLE URL sample nicks (top 10):")
    for n, c in Counter(triple_nicks).most_common(10):
        print(f"  {c:3d}  {n or '(empty)'}")

    # show context around one triplekey
    tm = TRIPLEKEY_RE.search(text)
    if tm:
        start = max(0, tm.start() - 200)
        snippet = text[start : tm.end() + 200]
        print("\nTriplekey context snippet:")
        print(repr(snippet[:500]))


if __name__ == "__main__":
    main()
