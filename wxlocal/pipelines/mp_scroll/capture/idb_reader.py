"""从微信 WeChatAppEx IndexedDB / Local Storage 读取订阅号列表缓存。"""
from __future__ import annotations

import html
import os
import re
import urllib.parse
from pathlib import Path

from wxlocal.pipelines.mp_scroll.capture.parsers import normalize_article_url

try:
    from wxlocal.pipelines.mp_scroll.capture.idb_blink import extract_triple_cards, extract_triple_cards_from_storage, normalize_triple_raw
    from wxlocal.pipelines.mp_scroll.capture.idb_leveldb import extract_triple_cards_from_leveldb_dirs
except ImportError:
    extract_triple_cards = None
    extract_triple_cards_from_storage = None
    extract_triple_cards_from_leveldb_dirs = None

    def normalize_triple_raw(raw: str) -> str:
        return raw

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILES = Path(os.environ.get("WECHAT_RADIUM_PROFILES", "")).expanduser() if os.environ.get(
    "WECHAT_RADIUM_PROFILES", ""
).strip() else None
if DEFAULT_PROFILES is None:
    from wxlocal.config.paths import default_radium_profiles

    DEFAULT_PROFILES = default_radium_profiles()
IDB_NAMES = (
    "https_mp.weixin.qq.com_0.indexeddb.leveldb",
    "weixin_xworker_0.indexeddb.leveldb",
)
LS_NAME = "Local Storage/leveldb"

URL_RE = re.compile(
    r"https?://mp\.weixin\.qq\.com/s(?:/[A-Za-z0-9_\-]{8,40}|[\?/][^\s\"'\\<>]{10,400})"
)
SHORT_URL_RE = re.compile(r"https?://mp\.weixin\.qq\.com/s/[A-Za-z0-9_\-]{8,40}")
CONTENT_URL_RE = re.compile(r'"content_url"\s*:\s*"(https?://[^"\\]+)"')
TITLE_JSON_RE = re.compile(r'"title"\s*:\s*"((?:\\.|[^"\\]){4,300})"')
NICK_RE = re.compile(
    r'"(?:nick_name|nickname|source_display_name)"\s*:\s*"((?:\\.|[^"\\]){2,120})"'
)
TRIPLEKEY_RE = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')


def article_key(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(parsed.query)
    biz = urllib.parse.unquote((q.get("__biz") or q.get("biz") or [""])[0])
    mid = (q.get("mid") or [""])[0]
    idx = (q.get("idx") or ["1"])[0]
    if biz and mid:
        return f"{biz}|{mid}|{idx}"
    return url


def url_has_sn(url: str) -> bool:
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return bool((q.get("sn") or [""])[0])


def triple_to_url(triple: str) -> str:
    triple = normalize_triple_raw(triple)
    biz, mid, idx = triple.rsplit("-", 2)
    raw = f"https://mp.weixin.qq.com/s?__biz={biz}&mid={mid}&idx={idx}"
    return normalize_article_url(raw) or raw


def find_storage_dirs(profiles_root: Path | None = None) -> list[Path]:
    root = profiles_root or DEFAULT_PROFILES
    if not root.is_dir():
        return []
    dirs: list[Path] = []
    for multitab in sorted(root.glob("multitab_*/IndexedDB")):
        for name in IDB_NAMES:
            path = multitab / name
            if path.is_dir():
                dirs.append(path)
        ls = multitab.parent / LS_NAME
        if ls.is_dir():
            dirs.append(ls)
    return dirs


def find_idb_dirs(profiles_root: Path | None = None) -> list[Path]:
    return [p for p in find_storage_dirs(profiles_root) if p.name.endswith(".leveldb")]


def _read_file_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b""


def read_storage_bytes(storage_dirs: list[Path] | None = None) -> bytes:
    dirs = storage_dirs or find_storage_dirs()
    parts: list[bytes] = []
    for store in dirs:
        for file in store.iterdir():
            if not file.is_file():
                continue
            if file.name == "LOCK":
                continue
            if file.suffix not in (".log", ".ldb") and file.name not in ("LOG", "LOG.old"):
                continue
            chunk = _read_file_bytes(file)
            if chunk:
                parts.append(chunk)
    return b"".join(parts)


def read_idb_bytes(idb_dirs: list[Path] | None = None, copy_dir: Path | None = None) -> bytes:
    # copy_dir kept for backward compatibility; direct read is preferred.
    _ = copy_dir
    return read_storage_bytes(idb_dirs or find_idb_dirs())


def _clean_json_str(value: str) -> str:
    value = html.unescape(value)
    value = value.encode().decode("unicode_escape", errors="replace")
    return re.sub(r"\s+", " ", value).strip()


def extract_urls(blob: bytes) -> list[str]:
    text = blob.decode("utf-8", errors="replace")
    urls: list[str] = []
    seen: set[str] = set()
    for match in URL_RE.finditer(text):
        url = normalize_article_url(match.group(0).replace("\\/", "/"))
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    for match in CONTENT_URL_RE.finditer(text):
        url = normalize_article_url(match.group(1).replace("\\/", "/"))
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def extract_cards(blob: bytes, *, storage_dirs: list[Path] | None = None) -> list[dict[str, str]]:
    """尽量从 blob 里配对 url + title + source_name。"""
    text = blob.decode("utf-8", errors="replace")
    cards: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url_raw: str, title: str = "", source: str = "") -> None:
        url = normalize_article_url(url_raw.replace("\\/", "/"))
        if not url or url in seen:
            return
        seen.add(url)
        cards.append(
            {
                "url": url,
                "title": _clean_json_str(title) if title else "",
                "source_name": _clean_json_str(source) if source else "",
            }
        )

    for match in CONTENT_URL_RE.finditer(text):
        start = max(0, match.start() - 1200)
        end = min(len(text), match.end() + 1200)
        window = text[start:end]
        title = ""
        source = ""
        tm = TITLE_JSON_RE.search(window)
        if tm:
            title = tm.group(1)
        nm = NICK_RE.search(window)
        if nm:
            source = nm.group(1)
        add(match.group(1), title, source)

    for match in URL_RE.finditer(text):
        start = max(0, match.start() - 800)
        end = min(len(text), match.end() + 800)
        window = text[start:end]
        title = ""
        source = ""
        tm = TITLE_JSON_RE.search(window)
        if tm:
            title = tm.group(1)
        nm = NICK_RE.search(window)
        if nm:
            source = nm.group(1)
        add(match.group(0), title, source)

    for triple in TRIPLEKEY_RE.findall(text):
        url = triple_to_url(triple)
        if not url:
            continue
        key = article_key(url)
        if key in {article_key(c["url"]) for c in cards}:
            continue
        add(url, source="idb:triplekey")

    # Blink 二进制 title（推荐流 triple 卡片）
    blink_cards: list[dict[str, str]] = []
    if extract_triple_cards_from_storage is not None and storage_dirs:
        blink_cards = extract_triple_cards_from_storage(storage_dirs)
    elif extract_triple_cards is not None:
        blink_cards = extract_triple_cards(blob)
    if extract_triple_cards_from_leveldb_dirs is not None and storage_dirs:
        ldb_cards = extract_triple_cards_from_leveldb_dirs(storage_dirs)
        by_triple = {c["triple"]: c for c in blink_cards}
        for card in ldb_cards:
            prev = by_triple.get(card["triple"])
            if prev is None:
                by_triple[card["triple"]] = card
            elif card.get("title") and not prev.get("title"):
                prev["title"] = card["title"]
                if card.get("source_name") and prev.get("source_name") == "idb:triplekey":
                    prev["source_name"] = card["source_name"]
        blink_cards = list(by_triple.values())
    if blink_cards:
        blink_by_triple = {c["triple"]: c for c in blink_cards}
        existing_keys = {article_key(c["url"]) for c in cards if c.get("url")}
        for tk, bc in blink_by_triple.items():
            url = triple_to_url(tk)
            if not url:
                continue
            key = article_key(url)
            if key not in existing_keys:
                add(
                    url,
                    bc.get("title", ""),
                    bc.get("source_name") or "idb:triplekey",
                )
                existing_keys.add(key)
        for card in cards:
            url = card.get("url", "")
            if not url or url_has_sn(url):
                continue
            key = article_key(url)
            triple_raw = None
            for tk, bc in blink_by_triple.items():
                if article_key(triple_to_url(tk)) == key:
                    triple_raw = tk
                    break
            if not triple_raw:
                continue
            bc = blink_by_triple[triple_raw]
            if bc.get("title"):
                prefer = bc.get("source_name") == "idb:leveldb" or not card.get("title")
                if prefer:
                    card["title"] = bc["title"]
            if bc.get("source_name") and card.get("source_name") == "idb:triplekey":
                card["source_name"] = bc["source_name"]

    return cards


def extract_titles(blob: bytes) -> list[str]:
    text = blob.decode("utf-8", errors="replace")
    titles: list[str] = []
    seen: set[str] = set()
    for match in TITLE_JSON_RE.finditer(text):
        title = _clean_json_str(match.group(1))
        if len(title) < 6 or title in seen:
            continue
        seen.add(title)
        titles.append(title)
    return titles


def scan_live() -> tuple[list[dict[str, str]], int]:
    dirs = find_storage_dirs()
    blob = read_storage_bytes(dirs)
    cards = extract_cards(blob, storage_dirs=dirs)
    if not cards:
        cards = [{"url": u, "title": "", "source_name": ""} for u in extract_urls(blob)]
    # 同一 biz|mid|idx 保留带 sn 的完整 URL
    best: dict[str, dict[str, str]] = {}
    for card in cards:
        url = card.get("url", "")
        if not url:
            continue
        key = article_key(url)
        prev = best.get(key)
        if prev is None or (url_has_sn(url) and not url_has_sn(prev["url"])):
            best[key] = card
    return list(best.values()), len(blob)
