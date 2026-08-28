"""Deep research: triplekey structure, title/sn neighbors, fetch without sn."""
from __future__ import annotations

import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from collections import Counter

from wxlocal.pipelines.mp_scroll.capture.idb_reader import read_storage_bytes, triple_to_url, url_has_sn

BACKUP = Path(os.environ.get("WECHAT_IDB_BACKUP", "")).expanduser()
PROXY = "http://127.0.0.1:6696"

TRIPLE_RE = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')
# UTF-16LE title fragments near triplekey in IDB binary
UTF16_RUN = re.compile(rb"(?:[\x20-\x7e]\x00){6,120}")
TITLE_JSON = re.compile(r'"title"\s*:\s*"((?:\\.|[^"\\]){4,200})"')
SN_JSON = re.compile(r'"sn"\s*:\s*"([0-9a-f]{8,32})"', re.I)


def utf16_runs(data: bytes, pos: int, radius: int = 1200) -> list[str]:
    chunk = data[max(0, pos - radius) : pos + radius]
    out: list[str] = []
    for m in UTF16_RUN.finditer(chunk):
        try:
            s = m.group(0).decode("utf-16le", errors="ignore").strip()
        except Exception:
            continue
        if len(s) >= 6 and any("\u4e00" <= c <= "\u9fff" for c in s):
            out.append(s[:120])
    return out


def probe_triple_structure() -> None:
    if not BACKUP.is_dir():
        print("Set WECHAT_IDB_BACKUP to an IndexedDB leveldb directory.")
        return
    blob = read_storage_bytes([BACKUP])
    text = blob.decode("utf-8", "replace")
    triples = TRIPLE_RE.findall(text)
    print("=" * 60)
    print("A. Triplekey structure in backup IDB")
    print("=" * 60)
    print(f"blob={len(blob)} unique triplekeys={len(set(triples))}")

    samples = list(dict.fromkeys(triples))[:5]
    for key in samples:
        pos = text.find(f'triplekey"{key}"')
        if pos < 0:
            continue
        window = text[max(0, pos - 400) : pos + 600]
        printable = "".join(ch if ch.isprintable() else "." for ch in window)
        utf16 = utf16_runs(blob, pos)
        titles = TITLE_JSON.findall(window)
        sns = SN_JSON.findall(window)
        print(f"\n--- {key} ---")
        print("ascii window:", printable[:350])
        print("utf16 runs:", utf16[:4])
        print("title json:", titles[:3])
        print("sn json:", sns[:3])

    from collections import Counter

    field_hits = Counter()

    for m in TRIPLE_RE.finditer(text):
        w = text[m.start() : m.end() + 400]
        for fname in (
            "title",
            "nick_name",
            "source_display_name",
            "content_url",
            "link",
            "url",
            "sn",
            "cover",
            "digest",
            "item_show_type",
            "rec_type",
            "rec_reason",
            "show_desc",
        ):
            if fname in w:
                field_hits[fname] += 1
    print("\nField names within 400 chars after triplekey:")
    for k, v in field_hits.most_common():
        print(f"  {k}: {v}")


def try_fetch_without_sn() -> None:
    print("\n" + "=" * 60)
    print("B. Can triple partial URL fetch title via 6696?")
    print("=" * 60)
    # sample triple from scroll batch
    samples = [
        "MzcwMDM3NDgzNQ==-2247483877-1",
        "MzIxMzA0Mzk4Nw==-2247485975-1",
    ]
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
    )
    ua = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49"
    )
    for key in samples:
        url = triple_to_url(key)
        print(f"\nkey={key}")
        print(f"url={url[:100]}")
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        try:
            with opener.open(req, timeout=15) as resp:
                html = resp.read(8000).decode("utf-8", "ignore")
            has_sn = "sn=" in resp.geturl() if hasattr(resp, "geturl") else False
            title_m = re.search(r"var msg_title = '([^']+)'|og:title\" content=\"([^\"]+)\"", html)
            title = (title_m.group(1) if title_m else title_m.group(2)) if title_m else ""
            print(f"final_url_has_sn={('sn=' in resp.geturl())} title={title[:60]!r}")
            print(f"redirect={resp.geturl()[:120]}")
        except Exception as e:
            print(f"fetch failed: {e}")


def scan_xworker_blob() -> None:
    print("\n" + "=" * 60)
    print("C. xworker blob store")
    print("=" * 60)
    profiles = __import__("paths").default_radium_profiles()
    blob_root = next(profiles.glob("*/IndexedDB/weixin_xworker_0.indexeddb.blob"), None)
    if blob_root is None:
        blob_root = profiles / "IndexedDB" / "weixin_xworker_0.indexeddb.blob"
    if not blob_root.is_dir():
        print("no xworker blob dir")
        return
    files = sorted(blob_root.rglob("*"), key=lambda p: p.stat().st_size if p.is_file() else 0, reverse=True)
    for f in files[:8]:
        if not f.is_file():
            continue
        data = f.read_bytes()
        text = data.decode("utf-8", "replace")
        tk = len(TRIPLE_RE.findall(text))
        urls = len(re.findall(r"mp\.weixin\.qq\.com/s", text))
        print(f"{f.relative_to(blob_root)} sz={f.stat().st_size} triple={tk} mp_urls={urls}")


if __name__ == "__main__":
    probe_triple_structure()
    try_fetch_without_sn()
    scan_xworker_blob()
