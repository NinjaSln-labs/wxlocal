"""Enumerate IDB binary schema + link triplekeys to titles via mid."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from wxlocal.pipelines.mp_scroll.capture.idb_reader import read_storage_bytes

BACKUP = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)

SKIP = {"png", "jpg", "http", "https", "com", "idx", "mid", "biz", "null", "true", "false"}
TRIPLE_RE2 = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')


def main() -> None:
    text = read_storage_bytes([BACKUP]).decode("utf-8", "replace")
    fields = Counter(re.findall(r'[\."]([a-z_]{3,32})[\."I]', text))
    print("Top field names in backup IDB blob:")
    for k, v in fields.most_common(50):
        if k in SKIP:
            continue
        print(f"  {v:4d}  {k}")

    for fname in (
        "title",
        "digest",
        "content",
        "desc",
        "show_desc",
        "rec_reason",
        "nick_name",
        "source_display_name",
    ):
        print(f"{fname}: {text.count(fname)}")

    print("\nSample Chinese title context:")
    for m in re.finditer("title", text):
        s = max(0, m.start() - 40)
        e = min(len(text), m.end() + 100)
        snip = "".join(c if c.isprintable() else "." for c in text[s:e])
        if any("\u4e00" <= c <= "\u9fff" for c in snip):
            print(snip[:160])
            break

    print("json title pattern:", len(re.findall(r'"title"\s*:\s*"', text)))

    print("\n=== mid linkage (triplekey -> title via mid) ===")
    triples = list(dict.fromkeys(TRIPLE_RE2.findall(text)))
    linked = 0
    for key in triples[:30]:
        _biz, mid, _idx = key.rsplit("-", 2)
        hits = []
        mid_pos = 0
        while True:
            p = text.find(mid, mid_pos)
            if p < 0:
                break
            window = text[max(0, p - 500) : p + 500]
            if ".title" in window:
                snip = "".join(c if c.isprintable() else "." for c in window)
                hits.append(snip[:200])
            mid_pos = p + 1
        if hits:
            linked += 1
            print(f"\n{key} title-windows={len(hits)}")
            print(hits[0][:160])
    print(f"linked by mid: {linked}/30")


if __name__ == "__main__":
    main()
