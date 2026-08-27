"""Test constructing article URL from geticon biz+mid."""
from __future__ import annotations

import re
import urllib.request

PROXY = "http://127.0.0.1:6696"
UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 MicroMessenger/8.0.49"
)

CASES = [
    ("opened-1", "MzU5NzMyNDIzOQ==", "2247485975"),
    ("opened-2", "Mzk3NTEyNzgwNQ==", "2247487435"),
]


def fetch(url: str) -> tuple[int, str, str]:
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Referer": "https://mp.weixin.qq.com/"},
    )
    with opener.open(req, timeout=25) as resp:
        page = resp.read().decode("utf-8", errors="replace")
    og = re.search(r'property="og:title"\s+content="([^"]+)"', page, re.I)
    title = og.group(1).strip() if og else ""
    if title.endswith("-微信公众平台"):
        title = title[: -len("-微信公众平台")].strip()
    flag = "verify" if ("verify" in page or "请在微信" in page) else "ok"
    return len(page), title, flag


def main() -> None:
    for label, biz, mid in CASES:
        url = f"https://mp.weixin.qq.com/s?__biz={biz}&mid={mid}&idx=1"
        try:
            n, title, flag = fetch(url)
            print(f"{label}: {flag} len={n} title={title[:70] or '(none)'}")
            print(f"  url={url}")
        except Exception as exc:
            print(f"{label}: ERR {exc}")


if __name__ == "__main__":
    main()
