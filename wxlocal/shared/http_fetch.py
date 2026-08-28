"""HTTP body fetch for WeChat article URLs."""
from __future__ import annotations

import time
import urllib.parse
import urllib.request

from wxlocal.pipelines.mp_scroll.capture.body_extract import extract_body_from_html

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "MicroMessenger/8.0.49 NetType/WIFI Language/zh_CN"
)


def fetch_http_body(url: str, opener: urllib.request.OpenerDirector | None = None) -> str:
    if not url or "mp.weixin.qq.com" not in url:
        return ""
    urls = [url]
    q = urllib.parse.urlparse(url).query
    p = urllib.parse.parse_qs(q)
    biz, mid, sn = (p.get("__biz") or [""])[0], (p.get("mid") or [""])[0], (p.get("sn") or [""])[0]
    idx = (p.get("idx") or ["1"])[0]
    if biz and mid and sn:
        std = f"https://mp.weixin.qq.com/s?__biz={biz}&mid={mid}&idx={idx}&sn={sn}"
        urls.append(std)
    open_fn = opener.open if opener is not None else urllib.request.urlopen
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Referer": "https://mp.weixin.qq.com/"})
            with open_fn(req, timeout=25) as resp:
                page = resp.read().decode("utf-8", errors="replace")
            body = extract_body_from_html(page)
            if len(body) > 80:
                return body
        except Exception:
            continue
        time.sleep(0.5)
    return ""
