"""订阅号 URL 注册表：查看、标记、按需抓标题/正文。

用法:
  python mp_registry.py scan
  python mp_registry.py list
  python mp_registry.py list --new
  python mp_registry.py search openobserve
  python mp_registry.py mark skillforge
  python mp_registry.py fetch-title --marked
  python mp_registry.py fetch-body openobserve
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from mp_capture.idb_registry import (
    build_opener,
    fetch_title_from_page,
    find_items,
    load_registry,
    mark_items,
    save_registry,
    scan_once,
)
from mp_dev_filter import is_dev_related

PROXY = os.environ.get("WECHAT_FETCH_PROXY", "http://127.0.0.1:6696")

def resolve_targets(registry: dict, args: argparse.Namespace) -> list[dict]:
    if args.marked:
        return find_items(registry, "", only_marked=True, limit=args.limit)
    query = " ".join(args.query or []).strip()
    if not query:
        return find_items(registry, "", only_new=args.new, limit=args.limit)
    return find_items(registry, query, only_new=args.new, limit=args.limit)


def cmd_scan(_: argparse.Namespace) -> None:
    result = scan_once()
    print(
        f"live={result['live_count']} total={result['total']} "
        f"new={len(result['new_urls'])} -> {result['registry_path']}"
    )


def cmd_list(args: argparse.Namespace) -> None:
    registry = load_registry()
    items = resolve_targets(registry, args)
    print(f"items={len(items)} / total={registry['meta'].get('total_urls', 0)}")
    for i, item in enumerate(items, 1):
        title = item.get("title") or "(no title)"
        mark = "*" if item.get("marked") else " "
        print(
            f"{mark}{i:>3}. [{item.get('status','?')}] {title[:72]} "
            f"| seen={item.get('seen_count',1)} | {item.get('last_seen','')}"
        )
        print(f"      {item.get('url','')[:110]}")


def cmd_mark(args: argparse.Namespace) -> None:
    registry = load_registry()
    query = " ".join(args.query or []).strip()
    if not query:
        print("请提供关键词，例如: python mp_registry.py mark skillforge")
        return
    urls = mark_items(registry, query)
    save_registry(registry)
    print(f"marked={len(urls)} query={query!r}")


def cmd_fetch_title(args: argparse.Namespace) -> None:
    registry = load_registry()
    items = resolve_targets(registry, args)
    if not items:
        print("没有匹配条目")
        return
    opener = build_opener()
    print(f"fetch-title {len(items)} 条 (proxy={PROXY})")
    for i, item in enumerate(items, 1):
        title, _ = fetch_title_from_page(item["url"], opener)
        if title:
            item["title"] = title
            item["status"] = "title_fetched"
        ok, reason = is_dev_related(title, item.get("summary", ""), item.get("source_name", ""))
        item["dev_related"] = ok
        item["filter_reason"] = reason
        print(f"  {i}/{len(items)} {title[:70] or '(empty)'} [{reason}]")
        time.sleep(0.4)
    save_registry(registry)


def cmd_fetch_body(args: argparse.Namespace) -> None:
    registry = load_registry()
    items = resolve_targets(registry, args)
    if not items:
        print("没有匹配条目")
        return
    opener = build_opener()
    print(f"fetch-body {len(items)} 条 (proxy={PROXY})")
    for i, item in enumerate(items, 1):
        title, body = fetch_title_from_page(item["url"], opener)
        if title:
            item["title"] = title
        if body:
            item["body"] = body
            item["body_source"] = "HTTP抓取"
            item["status"] = "body_fetched"
        from datetime import datetime

        item["fetched_at"] = datetime.now().isoformat(timespec="seconds")
        label = item.get("title") or item["url"][:60]
        print(f"  {i}/{len(items)} {label[:70]} body={len(body)} chars")
        time.sleep(0.5)
    save_registry(registry)


def main() -> None:
    parser = argparse.ArgumentParser(description="订阅号 URL 注册表")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="扫描 IndexedDB 并合并到注册表")
    p_scan.set_defaults(func=cmd_scan)

    for name, help_text in [
        ("list", "列出条目"),
        ("mark", "按关键词标记待抓取"),
        ("fetch-title", "抓取标题"),
        ("fetch-body", "抓取标题+正文"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("query", nargs="*", help="关键词或 URL 片段")
        p.add_argument("--new", action="store_true", help="仅未抓标题的新条目")
        p.add_argument("--marked", action="store_true", help="仅已标记条目")
        p.add_argument("--limit", type=int, default=50)
        if name == "list":
            p.set_defaults(func=cmd_list)
        elif name == "mark":
            p.set_defaults(func=cmd_mark)
        elif name == "fetch-title":
            p.set_defaults(func=cmd_fetch_title)
        else:
            p.set_defaults(func=cmd_fetch_body)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
