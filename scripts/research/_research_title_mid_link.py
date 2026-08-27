"""Link title records to triplekeys via shared mid in blob windows."""
from __future__ import annotations

import re
from pathlib import Path

from mp_capture.idb_reader import read_storage_bytes

BACKUP = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)
TRIPLE_RE = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')


def main() -> None:
    blob = read_storage_bytes([BACKUP])
    text = blob.decode("utf-8", "replace")
    triples = list(dict.fromkeys(TRIPLE_RE.findall(text)))

    linked = 0
    for key in triples[:30]:
        _biz, mid, _idx = key.rsplit("-", 2)
        # title marker windows containing same mid
        hits = []
        mid_pos = 0
        while True:
            p = text.find(mid, mid_pos)
            if p < 0:
                break
            window = text[max(0, p - 500) : p + 500]
            if ".title" in window or "title.c" in window:
                snip = "".join(c if c.isprintable() else "." for c in window)
                hits.append(snip[:200])
            mid_pos = p + 1
        if hits:
            linked += 1
            print(f"\n{key} mid={mid} title-windows={len(hits)}")
            print(hits[0][:180])

    print(f"\nlinked by mid proximity: {linked}/30")


if __name__ == "__main__":
    main()
