"""Extract plain-text article body from WeChat mp.weixin.qq.com HTML."""
from __future__ import annotations

import html
import re


def unescape_js_string(raw: str) -> str:
    """Decode JS single/double-quoted string escapes without breaking UTF-8."""
    out: list[str] = []
    i = 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw):
            n = raw[i + 1]
            if n == "n":
                out.append("\n")
                i += 2
                continue
            if n == "t":
                out.append("\t")
                i += 2
                continue
            if n == "r":
                out.append("\r")
                i += 2
                continue
            if n == "x" and i + 3 < len(raw):
                try:
                    out.append(chr(int(raw[i + 2 : i + 4], 16)))
                    i += 4
                    continue
                except ValueError:
                    pass
            if n in ("'", '"', "\\", "/"):
                out.append(n)
                i += 2
                continue
        out.append(raw[i])
        i += 1
    text = html.unescape("".join(out))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _html_to_text(body_html: str) -> str:
    body_html = re.sub(r"<script[^>]*>.*?</script>", "", body_html, flags=re.DOTALL | re.I)
    body_html = re.sub(r"<style[^>]*>.*?</style>", "", body_html, flags=re.DOTALL | re.I)
    body_html = re.sub(r"<br\s*/?>", "\n", body_html, flags=re.I)
    body_html = re.sub(r"</p>", "\n\n", body_html, flags=re.I)
    body_html = re.sub(r"</(h[1-6]|section|div|li)>", "\n", body_html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", body_html)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract_js_string_after(page: str, key: str) -> str:
    """Parse JS object field value after ``key:`` (handles long/special strings)."""
    idx = page.find(key)
    if idx < 0:
        return ""
    rest = page[idx + len(key) : idx + len(key) + 500_000]
    rest = rest.lstrip(" \t:\n\r")
    if not rest or rest[0] not in ("'", '"'):
        return ""
    quote = rest[0]
    raw_chars: list[str] = []
    i = 1
    while i < len(rest):
        ch = rest[i]
        if ch == "\\" and i + 1 < len(rest):
            raw_chars.append(ch)
            raw_chars.append(rest[i + 1])
            i += 2
            continue
        if ch == quote:
            break
        raw_chars.append(ch)
        i += 1
    return unescape_js_string("".join(raw_chars))


def extract_body_from_html(html_text: str) -> str:
    """Best-effort body extraction from article page HTML."""
    dom_patterns = [
        r'id=["\']js_content["\'][^>]*>(.*?)</div>\s*<script',
        r'id=["\']js_content["\'][^>]*>(.*)',
        r'class=["\']rich_media_content[^"\']*["\'][^>]*>(.*?)</div>',
        r'id=["\']img-content["\'][^>]*>(.*?)</div>\s*<script',
        r"<article[^>]*>(.*?)</article>",
        r'class=["\']ltx_page_content["\'][^>]*>(.*?)</div>\s*<footer',
    ]
    for pat in dom_patterns:
        m = re.search(pat, html_text, re.DOTALL | re.IGNORECASE)
        if m:
            text = _html_to_text(m.group(1))
            if len(text) > 80:
                return text

    for key in ("content_noencode", "msg_desc", "desc"):
        text = _extract_js_string_after(html_text, key)
        text = re.sub(r"<[^>]+>", "", text).strip()
        if len(text) > 80:
            return text

    js_patterns = [
        r"content_noencode\s*:\s*'((?:\\.|[^'\\])*)'",
        r'content_noencode\s*:\s*"((?:\\.|[^"\\])*)"',
        r"window\.content_noencode\s*=\s*'((?:\\.|[^'\\])*)'",
        r'window\.content_noencode\s*=\s*"((?:\\.|[^"\\])*)"',
    ]
    for pat in js_patterns:
        best = ""
        for s in re.findall(pat, html_text):
            t = unescape_js_string(s)
            t = re.sub(r"<[^>]+>", "", t).strip()
            if len(t) > len(best):
                best = t
        if len(best) > 80:
            return best

    json_patterns = [
        r'"desc"\s*:\s*"((?:\\.|[^"\\])*)"',
        r'"content_noencode"\s*:\s*"((?:\\.|[^"\\])*)"',
        r'"content"\s*:\s*"((?:\\.|[^"\\]){80,})"',
    ]
    for pat in json_patterns:
        best = ""
        for s in re.findall(pat, html_text):
            t = unescape_js_string(s)
            t = re.sub(r"<[^>]+>", "", t).strip()
            if len(t) > len(best):
                best = t
        if len(best) > 80:
            return best
    return ""
