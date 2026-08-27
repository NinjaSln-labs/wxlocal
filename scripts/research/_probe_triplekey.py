"""Extract triplekey (biz-mid-idx) entries from IDB."""
from __future__ import annotations

import re

from mp_capture.idb_reader import extract_urls, read_storage_bytes

TRIPLE_RE = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')
URL_RE = re.compile(r"https?://mp\.weixin\.qq\.com/s[^\s\"'\\<>]{10,400}")


def triple_to_url(key: str) -> str:
    biz, mid, idx = key.split("-", 2)
    return f"https://mp.weixin.qq.com/s?__biz={biz}&mid={mid}&idx={idx}"


def _article_key(biz: str, mid: str, idx: str) -> str:
    return f"{biz}-{mid}-{idx}"


def main() -> None:
    import urllib.parse

    text = read_storage_bytes().decode("utf-8", errors="replace")
    triples = sorted(set(TRIPLE_RE.findall(text)))
    urls = set(extract_urls(read_storage_bytes()))
    triple_keys = set(triples)

    url_keys: set[str] = set()
    for u in urls:
        q = urllib.parse.urlparse(u).query
        p = urllib.parse.parse_qs(q)
        biz = urllib.parse.unquote(p.get("__biz", [""])[0])
        mid = p.get("mid", [""])[0]
        idx = p.get("idx", ["1"])[0]
        if biz and mid:
            url_keys.add(_article_key(biz, mid, idx))

    only_triple = sorted(triple_keys - url_keys)
    print(f"full_urls={len(urls)} triplekeys={len(triples)} overlap={len(triple_keys & url_keys)}")
    print(f"triple_only={len(only_triple)} url_only={len(url_keys - triple_keys)}")
    for k in only_triple[:12]:
        print(" + triple_only:", k)


if __name__ == "__main__":
    main()
