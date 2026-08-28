"""Check if triplekey records have .title. in binary schema nearby."""
from __future__ import annotations

import re
from pathlib import Path

from wxlocal.pipelines.mp_scroll.capture.idb_reader import read_storage_bytes

BACKUP = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)

TRIPLE_RE = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')
# binary schema: .title."actual title text"
TITLE_DOT = re.compile(r'\.title"([^"]{4,200})"')


def main() -> None:
    blob = read_storage_bytes([BACKUP])
    text = blob.decode("utf-8", "replace")

    keys = list(dict.fromkeys(TRIPLE_RE.findall(text)))
    print(f"unique triplekeys={len(keys)}")
    print(f"global .title\" hits={len(TITLE_DOT.findall(text))}")

    with_title = 0
    for key in keys[:30]:
        pos = text.find(f'triplekey"{key}"')
        if pos < 0:
            continue
        window = text[max(0, pos - 1500) : pos + 2500]
        titles = TITLE_DOT.findall(window)
        # filter noise
        titles = [t for t in titles if any("\u4e00" <= c <= "\u9fff" for c in t) or "AI" in t.upper()]
        if titles:
            with_title += 1
            print(f"\n{key}")
            for t in titles[:2]:
                print(f"  title: {t[:100]}")

    print(f"\nOf first 30 triplekeys, {with_title} have .title. in ±2500 window")

    # also check full URL records
    full_sn = text.count("sn=")
    print(f"sn= occurrences in blob: {full_sn}")


if __name__ == "__main__":
    main()
