"""Parse Blink-style title fields and link to triplekeys."""
from __future__ import annotations

import re
from pathlib import Path

from mp_capture.idb_reader import read_storage_bytes

BACKUP = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)

TITLE_MARK = b"\x05title\x00c"
NICK_MARK = b"\x08nick_name"
TRIPLE_BIN = re.compile(rb'triplekey"\x1d([\w=+-]+-\d{8,13}-\d+)"')
TRIPLE_TXT = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')


def read_utf16_le(data: bytes) -> str:
    out = bytearray()
    i = 0
    while i + 1 < len(data):
        if data[i] == 0 and data[i + 1] == 0:
            break
        out.extend(data[i : i + 2])
        i += 2
    return out.decode("utf-16le", errors="ignore").strip()


def extract_title(chunk: bytes) -> str:
    i = chunk.find(TITLE_MARK)
    if i < 0:
        return ""
    return read_utf16_le(chunk[i + len(TITLE_MARK) : i + len(TITLE_MARK) + 800])


def extract_nick(chunk: bytes) -> str:
    i = chunk.find(NICK_MARK)
    if i < 0:
        return ""
    # nick may be ascii or utf16 - try after marker
    raw = chunk[i + len(NICK_MARK) : i + len(NICK_MARK) + 200]
    if raw[:1] == b'"':
        m = re.match(rb'"([^"]{2,80})"', raw)
        if m:
            return m.group(1).decode("utf-8", errors="ignore")
    return read_utf16_le(raw)


def main() -> None:
    blob = read_storage_bytes([BACKUP])
    text = blob.decode("utf-8", "replace")

    # all titles in blob
    titles_found = 0
    pos = 0
    while True:
        i = blob.find(TITLE_MARK, pos)
        if i < 0:
            break
        t = extract_title(blob[i : i + 1200])
        if t and any("\u4e00" <= c <= "\u9fff" for c in t):
            titles_found += 1
        pos = i + len(TITLE_MARK)

    print(f"Chinese titles via Blink marker: {titles_found}")

    triples = list(dict.fromkeys(m.group(1).decode() for m in TRIPLE_BIN.finditer(blob)))
    if not triples:
        triples = list(dict.fromkeys(TRIPLE_TXT.findall(text)))
    print(f"unique triplekeys: {len(triples)}")

    both = 0
    for key in triples[:50]:
        needle = f'triplekey"\x1d{key}"'.encode("latin1")
        p = blob.find(needle)
        if p < 0:
            p = text.find(f'triplekey"{key}"')
            if p < 0:
                continue
        window = blob[max(0, p - 8000) : p + 12000]
        title = extract_title(window)
        nick = extract_nick(window)
        if title:
            both += 1
            print(f"\n{key}")
            print(f"  title: {title[:100]}")
            if nick:
                print(f"  nick: {nick}")

    print(f"\ntriplekeys with title in ±8k window: {both}/{min(50, len(triples))}")


if __name__ == "__main__":
    main()
