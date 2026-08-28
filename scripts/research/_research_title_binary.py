"""Try decode .title.c binary strings near triplekeys."""
from __future__ import annotations

import re
from pathlib import Path

from wxlocal.pipelines.mp_scroll.capture.idb_reader import read_storage_bytes

BACKUP = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)

TRIPLE_RE = re.compile(rb'triplekey"\x1d([\w=+-]+-\d{8,13}-\d+)"')
TRIPLE_RE2 = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')


def decode_title_after_marker(chunk: bytes) -> list[str]:
    """Find .title.c markers and try decode following bytes."""
    out: list[str] = []
    marker = b".title.c"
    pos = 0
    while True:
        i = chunk.find(marker, pos)
        if i < 0:
            break
        raw = chunk[i + len(marker) : i + len(marker) + 400]
        # try utf-16le from various offsets
        for off in range(0, 8):
            seg = raw[off : off + 300]
            if len(seg) < 10:
                continue
            try:
                s = seg.decode("utf-16le", errors="ignore")
            except Exception:
                continue
            s = "".join(c for c in s if c.isprintable() or "\u4e00" <= c <= "\u9fff").strip()
            if len(s) >= 8 and any("\u4e00" <= c <= "\u9fff" for c in s):
                out.append(s[:120])
                break
        pos = i + len(marker)
    return out


def main() -> None:
    blob = read_storage_bytes([BACKUP])
    text = blob.decode("utf-8", "replace")
    keys = list(dict.fromkeys(TRIPLE_RE2.findall(text)))
    print(f"triplekeys={len(keys)}")

    matched = 0
    for key in keys[:25]:
        needle = f'triplekey"{key}"'.encode()
        pos = blob.find(needle)
        if pos < 0:
            continue
        window = blob[max(0, pos - 3000) : pos + 5000]
        titles = decode_title_after_marker(window)
        if titles:
            matched += 1
            print(f"\n{key}")
            for t in titles[:2]:
                print(f"  {t}")

    print(f"\nmatched {matched}/25 triplekeys with decodable .title.c nearby")


if __name__ == "__main__":
    main()
