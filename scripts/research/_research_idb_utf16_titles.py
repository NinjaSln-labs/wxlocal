"""Extract UTF-16 title candidates adjacent to triplekeys in IDB backup."""
from __future__ import annotations

import re
from pathlib import Path

from wxlocal.pipelines.mp_scroll.capture.idb_reader import read_storage_bytes

BACKUP = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)

TRIPLE_RE = re.compile(rb'triplekey"\x1d([\w=+-]+-\d{8,13}-\d+)"')
# also plain ascii triplekey from utf-8 decode path
TRIPLE_RE2 = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')


def utf16_strings(data: bytes, pos: int, before: int = 2000, after: int = 4000) -> list[str]:
    chunk = data[max(0, pos - before) : pos + after]
    out: list[str] = []
    i = 0
    while i < len(chunk) - 3:
        # look for UTF-16LE run: printable ascii/high byte pairs
        if chunk[i + 1] == 0 and 32 <= chunk[i] <= 126:
            j = i
            chars: list[str] = []
            while j < len(chunk) - 1 and chunk[j + 1] == 0:
                c = chunk[j]
                if c == 0:
                    break
                if 32 <= c <= 126 or c >= 128:
                    try:
                        chars.append(bytes([c, chunk[j + 1]]).decode("utf-16le"))
                    except Exception:
                        break
                else:
                    break
                j += 2
            s = "".join(chars).strip()
            if len(s) >= 8 and any("\u4e00" <= c <= "\u9fff" for c in s):
                out.append(s[:200])
            i = max(i + 2, j)
        else:
            i += 1
    # dedupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def main() -> None:
    blob = read_storage_bytes([BACKUP])
    text = blob.decode("utf-8", "replace")
    keys = list(dict.fromkeys(TRIPLE_RE2.findall(text)))
    print(f"triplekeys={len(keys)}")

    with_title = 0
    for key in keys[:20]:
        needle = f'triplekey"{key}"'.encode("utf-8", errors="ignore")
        pos = blob.find(needle)
        if pos < 0:
            pos = text.find(f'triplekey"{key}"')
            if pos < 0:
                continue
        titles = utf16_strings(blob, pos)
        # filter plausible article titles
        cand = [t for t in titles if len(t) >= 10 and not t.startswith("M")]
        if cand:
            with_title += 1
        print(f"\n{key}")
        for t in cand[:3]:
            print(f"  title? {t}")

    print(f"\nOf first 20 triplekeys, {with_title} have UTF-16 title candidates nearby")

    # scan for 'title' as utf-16 field name
    title_field = "title".encode("utf-16le")
    print(f"utf16 'title' field occurrences in blob: {blob.count(title_field)}")


if __name__ == "__main__":
    main()
