"""分析 raw/ 抓包：找列表 API、文章元数据。"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

RAW = Path(r"F:\ext\knowledge-base\wechat\mp-capture\raw")


def parse_header(text: str) -> dict:
    meta = {}
    for line in text.splitlines()[:10]:
        if line.startswith("# host="):
            meta["host"] = line[6:]
        elif line.startswith("# path="):
            meta["path"] = line[7:]
        elif line.startswith("# content-type="):
            meta["ctype"] = line[17:]
        elif line.startswith("# bytes="):
            meta["bytes"] = int(line[8:] or 0)
    body = text.split("\n\n", 1)[-1] if "\n\n" in text else ""
    return {**meta, "body": body}


def main() -> None:
    files = sorted(RAW.glob("*.txt"))
    print(f"raw files: {len(files)}")

    hosts = Counter()
    paths = Counter()
    json_hits = []
    title_hits = []
    url_hits = []
    biz_hits = []

    for fp in files:
        text = fp.read_text(encoding="utf-8", errors="replace")
        meta = parse_header(text)
        host = meta.get("host", "")
        path = meta.get("path", "")
        body = meta.get("body", "")
        hosts[host] += 1
        # normalize path for counting
        pkey = re.sub(r"biz=[^&]+", "biz=*", path)
        pkey = re.sub(r"mid=\d+", "mid=*", pkey)
        pkey = re.sub(r"r=[0-9.]+", "r=*", pkey)
        paths[f"{host}{pkey}"] += 1

        if "application/json" in meta.get("ctype", "") and len(body) > 50:
            if any(k in body for k in ("title", "content_url", "comm_msg", "app_msg", "nick_name")):
                json_hits.append((fp.name, host, path[:80], body[:200]))

        if re.search(r'"title"\s*:', body) or "<title>" in body:
            if "jsmonitor" not in path and "验证" not in body[:100]:
                title_hits.append((fp.name, path[:80], body[:150]))

        for m in re.finditer(r"mp\.weixin\.qq\.com/s[^\s\"'<>]*", body):
            url_hits.append(m.group(0)[:120])

        for m in re.finditer(r"[?&](?:__)?biz=([A-Za-z0-9_=+%-]+).*?mid=(\d+)", body):
            biz_hits.append((m.group(1)[:20], m.group(2), path[:60]))

    print("\n=== hosts ===")
    for h, n in hosts.most_common():
        print(f"  {n:4d}  {h}")

    print("\n=== paths (normalized) ===")
    for p, n in paths.most_common(25):
        print(f"  {n:4d}  {p[:100]}")

    print(f"\n=== json with article keys: {len(json_hits)} ===")
    for x in json_hits[:15]:
        print(f"  {x[0][:50]}")
        print(f"    {x[1]}{x[2]}")
        print(f"    {x[3][:120]}...")

    print(f"\n=== title hits: {len(title_hits)} ===")
    for x in title_hits[:10]:
        print(f"  {x[0][:45]} | {x[1]}")

    print(f"\n=== mp.weixin.qq.com/s in body: {len(url_hits)} ===")
    for u in sorted(set(url_hits))[:15]:
        print(f"  {u}")

    print(f"\n=== biz+mid in body: {len(biz_hits)} ===")
    for b in sorted(set(biz_hits))[:15]:
        print(f"  biz={b[0]} mid={b[1]} path={b[2]}")


if __name__ == "__main__":
    main()
