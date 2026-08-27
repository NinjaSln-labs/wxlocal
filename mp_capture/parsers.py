"""从 HTTP 响应 / JSON / XML 中提取公众号文章卡片。"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
from typing import Any

from mp_capture.constants import ARTICLE_URL_RE, URL_KEEP_KEYS

TITLE_KEYS = ("title", "Title", "itemtitle", "main_title", "nick_name", "nickname", "source_display_name")
URL_KEYS = ("content_url", "url", "link", "contenturl", "source_url", "article_url")
SUMMARY_KEYS = ("digest", "desc", "description", "summary", "abstract", "itemshowtype")
SOURCE_KEYS = ("nick_name", "nickname", "source_display_name", "sourcedisplayname", "author", "bizusername")


def normalize_article_url(url: str) -> str:
    if not url or "mp.weixin.qq.com" not in url:
        return ""
    url = html.unescape(url.strip())
    if url.startswith("//"):
        url = "https:" + url
    parsed = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(parsed.query)
    # geticon 等接口用 biz= 而非 __biz=
    biz = (q.get("__biz") or q.get("biz") or [""])[0]
    mid = (q.get("mid") or [""])[0]
    sn = (q.get("sn") or [""])[0]
    idx = (q.get("idx") or ["1"])[0]
    if biz and mid and (sn or parsed.path.rstrip("/").endswith("/s")):
        kept = {"__biz": biz, "mid": mid, "idx": idx}
        if sn:
            kept["sn"] = sn
        for k in URL_KEEP_KEYS:
            if k in q and k not in kept:
                kept[k] = q[k][0]
        return f"https://mp.weixin.qq.com/s?{urllib.parse.urlencode(kept)}"
    if parsed.path.rstrip("/").endswith("/s") and q:
        kept = {k: q[k][0] for k in URL_KEEP_KEYS if k in q}
        if kept.get("__biz") and kept.get("mid"):
            return f"https://mp.weixin.qq.com/s?{urllib.parse.urlencode(kept)}"
    if "/mp/conference/" in url or "/share" in parsed.path:
        return ""
    return url.split("#")[0]


def _clean_title(t: str) -> str:
    t = html.unescape((t or "").strip())
    t = re.sub(r"\s+", " ", t)
    return t[:500]


def _walk(obj: Any, path: str = "") -> list[dict]:
    found: list[dict] = []
    if isinstance(obj, dict):
        title = ""
        for k in TITLE_KEYS:
            if k in obj and isinstance(obj[k], str) and len(obj[k].strip()) > 4:
                title = _clean_title(obj[k])
                break
        url = ""
        for k in URL_KEYS:
            if k in obj and isinstance(obj[k], str) and "mp.weixin.qq.com" in obj[k]:
                url = normalize_article_url(obj[k])
                break
        summary = ""
        for k in SUMMARY_KEYS:
            if k in obj and isinstance(obj[k], str):
                summary = _clean_title(obj[k])[:500]
                break
        source = ""
        for k in SOURCE_KEYS:
            if k in obj and isinstance(obj[k], str):
                source = _clean_title(obj[k])[:120]
                break
        if title and (url or summary):
            found.append(
                {
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "source_name": source,
                    "parse_path": path,
                }
            )
        for k, v in obj.items():
            found.extend(_walk(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(_walk(v, f"{path}[{i}]"))
    return found


def extract_from_json(text: str) -> list[dict]:
    try:
        data = json.loads(text)
    except Exception:
        return []
    items = _walk(data)
    return _dedupe_items(items)


def extract_from_xml(text: str) -> list[dict]:
    items: list[dict] = []
    for block in re.findall(r"<appmsg[\s\S]*?</appmsg>", text, re.I):
        title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", block, re.S)
        if not title_m:
            continue
        title = _clean_title(title_m.group(1) or title_m.group(2) or "")
        url_m = re.search(r"<url><!\[CDATA\[(.*?)\]\]></url>|<url>(.*?)</url>", block, re.S)
        url = normalize_article_url(html.unescape((url_m.group(1) or url_m.group(2) or ""))) if url_m else ""
        desc_m = re.search(r"<des><!\[CDATA\[(.*?)\]\]></des>|<des>(.*?)</des>", block, re.S)
        summary = _clean_title(desc_m.group(1) or desc_m.group(2) or "") if desc_m else ""
        src_m = re.search(
            r"<sourcedisplayname><!\[CDATA\[(.*?)\]\]></sourcedisplayname>|<sourcedisplayname>(.*?)</sourcedisplayname>",
            block,
            re.S,
        )
        source = _clean_title(src_m.group(1) or src_m.group(2) or "") if src_m else ""
        if title:
            items.append({"title": title, "url": url, "summary": summary, "source_name": source, "parse_path": "xml.appmsg"})
    return _dedupe_items(items)


def extract_urls_from_text(text: str) -> list[dict]:
    items: list[dict] = []
    for m in ARTICLE_URL_RE.finditer(text):
        url = normalize_article_url(m.group(0))
        if url:
            items.append({"title": "", "url": url, "summary": "", "source_name": "", "parse_path": "regex.url"})
    return _dedupe_items(items)


def extract_from_html(text: str, page_url: str = "") -> list[dict]:
    items: list[dict] = []
    og_title = re.search(r'property="og:title"\s+content="([^"]+)"', text, re.I)
    title = _clean_title(og_title.group(1)) if og_title else ""
    if title and page_url and "mp.weixin.qq.com/s" in page_url:
        items.append(
            {
                "title": title,
                "url": normalize_article_url(page_url),
                "summary": "",
                "source_name": "",
                "parse_path": "html.og:title",
            }
        )
    # 内嵌 JSON
    for m in re.finditer(r"var\s+msg_(?:cdn_)?url\s*=\s*['\"]([^'\"]+)['\"]", text):
        url = normalize_article_url(m.group(1))
        if url:
            items.append({"title": title, "url": url, "summary": "", "source_name": "", "parse_path": "html.js"})
    items.extend(extract_urls_from_text(text))
    return _dedupe_items(items)


def extract_from_body(body: bytes | str, content_type: str = "", page_url: str = "") -> list[dict]:
    if isinstance(body, bytes):
        text = body.decode("utf-8", errors="replace")
    else:
        text = body or ""
    if not text.strip():
        return []

    ct = (content_type or "").lower()
    items: list[dict] = []

    if "json" in ct or text.lstrip().startswith(("{", "[")):
        items.extend(extract_from_json(text))
    if "<appmsg" in text or "<title>" in text:
        items.extend(extract_from_xml(text))
    if "html" in ct or "<html" in text.lower():
        items.extend(extract_from_html(text, page_url))
    if not items:
        items.extend(extract_urls_from_text(text))
    return _dedupe_items(items)


def _dedupe_items(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for it in items:
        url = normalize_article_url(it.get("url") or "")
        title = _clean_title(it.get("title") or "")
        key = url or f"title:{title}"
        if not key or key in seen:
            continue
        if not title and not url:
            continue
        seen.add(key)
        it = dict(it)
        it["url"] = url
        it["title"] = title
        out.append(it)
    return out
