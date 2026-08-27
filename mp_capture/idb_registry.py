"""IndexedDB 注册表 + 标题抓取 + 开发向导出。"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from export_mp_dev import fetch_http_body
from mp_capture.body_extract import extract_body_from_html
from mp_capture.feed_ocr import scan_visible_feed, title_registry_key
from mp_capture.idb_reader import article_key, scan_live, url_has_sn
from ninjasin_dedup import dedup_key, load_known_keys
from mp_dev_filter import is_dev_related
from paths import (
    MP_CAPTURE_EXPORT,
    MP_CAPTURE_REGISTRY,
    MP_SCROLL_ARCHIVE,
    MP_SCROLL_EXPORT,
    MP_SCROLL_KB,
    ensure_mp_capture_dirs,
    ensure_mp_scroll_dirs,
)

PROXY = os.environ.get("WECHAT_FETCH_PROXY", "http://127.0.0.1:6696")
UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "MicroMessenger/8.0.49"
)
ENRICH_BATCH = int(os.environ.get("MP_SCROLL_ENRICH_BATCH", "20"))
BODY_ENRICH_BATCH = int(os.environ.get("MP_SCROLL_BODY_BATCH", "15"))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _empty_registry() -> dict[str, Any]:
    return {
        "meta": {
            "created_at": _now(),
            "updated_at": _now(),
            "last_scan_at": None,
            "last_live_count": 0,
            "total_urls": 0,
        },
        "items": {},
    }


def load_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or MP_CAPTURE_REGISTRY
    if not registry_path.is_file():
        return _empty_registry()
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_registry()
    data.setdefault("meta", {})
    data.setdefault("items", {})
    return data


def save_registry(data: dict[str, Any], path: Path | None = None) -> Path:
    ensure_mp_capture_dirs()
    registry_path = path or MP_CAPTURE_REGISTRY
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    data["meta"]["updated_at"] = _now()
    data["meta"]["total_urls"] = len(data.get("items", {}))
    tmp = registry_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(registry_path)
    export_registry_latest(data)
    return registry_path


def export_registry_latest(data: dict[str, Any]) -> Path:
    ensure_mp_capture_dirs()
    items = sorted(
        data.get("items", {}).values(),
        key=lambda x: x.get("last_seen", ""),
        reverse=True,
    )
    payload = {"meta": data.get("meta", {}), "items": items}
    latest = MP_CAPTURE_EXPORT / "idb_registry_latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return latest


def _find_item_by_key(items: dict[str, dict[str, Any]], key: str) -> tuple[str | None, dict[str, Any] | None]:
    for url, row in items.items():
        row_key = row.get("article_key") or article_key(url)
        if row_key == key:
            return url, row
    return None, None


def merge_cards(registry: dict[str, Any], cards: list[dict[str, str]], *, live_count: int | None = None) -> list[str]:
    when = _now()
    items: dict[str, dict[str, Any]] = registry.setdefault("items", {})
    new_urls: list[str] = []
    for card in cards:
        url = card.get("url", "")
        if not url:
            continue
        key = article_key(url)
        existing_url, row = _find_item_by_key(items, key)
        if row is None:
            title = card.get("title", "")
            row = {
                "url": url,
                "article_key": key,
                "url_kind": "full" if url_has_sn(url) else "triple",
                "first_seen": when,
                "last_seen": when,
                "seen_count": 1,
                "title": title,
                "summary": "",
                "source_name": card.get("source_name", ""),
                "status": (
                    "title_idb"
                    if title and not url_has_sn(url)
                    else ("awaiting_sn" if not url_has_sn(url) else "discovered")
                ),
                "marked": False,
                "body": "",
                "fetched_at": None,
            }
            if title:
                ok, reason = is_dev_related(title, "", row.get("source_name", ""))
                row["dev_related"] = ok
                row["filter_reason"] = reason
            items[url] = row
            new_urls.append(url)
            continue

        row["last_seen"] = when
        if card.get("title") and not row.get("title"):
            row["title"] = card["title"]
            if not url_has_sn(url):
                row["status"] = "title_idb"
                ok, reason = is_dev_related(card["title"], "", row.get("source_name", ""))
                row["dev_related"] = ok
                row["filter_reason"] = reason
        elif card.get("title") and row.get("status") == "awaiting_sn" and not row.get("title"):
            row["title"] = card["title"]
            row["status"] = "title_idb"
            ok, reason = is_dev_related(card["title"], "", row.get("source_name", ""))
            row["dev_related"] = ok
            row["filter_reason"] = reason
        if card.get("source_name") and not row.get("source_name"):
            row["source_name"] = card["source_name"]

        if existing_url != url and url_has_sn(url) and not url_has_sn(existing_url):
            row["url"] = url
            row["url_kind"] = "full"
            row["status"] = "discovered" if row.get("status") == "awaiting_sn" else row.get("status", "discovered")
            items[url] = row
            del items[existing_url]
        elif url_has_sn(url):
            row["url_kind"] = "full"
    meta = registry.setdefault("meta", {})
    meta["last_scan_at"] = when
    if live_count is not None:
        meta["last_live_count"] = live_count
    meta["total_urls"] = len(items)
    return new_urls


def merge_ocr_titles(registry: dict[str, Any], titles: list[str]) -> list[str]:
    when = _now()
    items: dict[str, dict[str, Any]] = registry.setdefault("items", {})
    new_keys: list[str] = []
    existing_titles = {
        (row.get("title") or "").strip().lower()
        for row in items.values()
        if row.get("title")
    }
    for title in titles:
        norm = title.strip()
        if not norm or norm.lower() in existing_titles:
            continue
        key = title_registry_key(norm)
        if key in items:
            items[key]["last_seen"] = when
            continue
        items[key] = {
            "url": key,
            "article_key": key,
            "url_kind": "ocr",
            "first_seen": when,
            "last_seen": when,
            "seen_count": 1,
            "title": norm,
            "summary": "",
            "source_name": "ocr:feed",
            "status": "title_ocr",
            "marked": False,
            "body": "",
            "fetched_at": when,
        }
        ok, reason = is_dev_related(norm, "", "ocr:feed")
        items[key]["dev_related"] = ok
        items[key]["filter_reason"] = reason
        existing_titles.add(norm.lower())
        new_keys.append(key)
    return new_keys


def scan_once(path: Path | None = None, *, ocr: bool = False) -> dict[str, Any]:
    cards, blob_size = scan_live()
    full_n = sum(1 for c in cards if url_has_sn(c.get("url", "")))
    triple_n = len(cards) - full_n
    registry = load_registry(path)
    new_urls = merge_cards(registry, cards, live_count=len(cards))
    ocr_stats: dict[str, Any] = {"enabled": False, "titles": [], "ocr_new": 0}
    ocr_new: list[str] = []
    if ocr:
        ocr_stats = scan_visible_feed()
        if ocr_stats.get("titles"):
            ocr_new = merge_ocr_titles(registry, ocr_stats["titles"])
        ocr_stats["ocr_new"] = len(ocr_new)
    registry["meta"]["last_idb_bytes"] = blob_size
    registry["meta"]["last_scan_full"] = full_n
    registry["meta"]["last_scan_triple"] = triple_n
    registry["meta"]["last_ocr_titles"] = len(ocr_stats.get("titles", []))
    registry["meta"]["last_ocr_new"] = len(ocr_new)
    save_registry(registry, path)
    return {
        "live_count": len(cards),
        "full_count": full_n,
        "triple_count": triple_n,
        "total": len(registry["items"]),
        "new_urls": new_urls,
        "ocr_titles": len(ocr_stats.get("titles", [])),
        "ocr_new": len(ocr_new),
        "ocr_error": ocr_stats.get("error", ""),
        "registry_path": str(path or MP_CAPTURE_REGISTRY),
    }


def build_opener() -> urllib.request.OpenerDirector:
    handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
    return urllib.request.build_opener(handler)


def fetch_title_from_page(url: str, opener: urllib.request.OpenerDirector) -> tuple[str, str]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": UA, "Referer": "https://mp.weixin.qq.com/"},
        )
        with opener.open(req, timeout=30) as resp:
            page = resp.read().decode("utf-8", errors="replace")
        body = extract_body_from_html(page)
        og = re.search(r'property="og:title"\s+content="([^"]+)"', page, re.I)
        if og:
            title = og.group(1).strip()
            if title.endswith("-微信公众平台"):
                title = title[: -len("-微信公众平台")].strip()
            return title, body
        if body:
            return "", body
    except Exception:
        pass
    body = fetch_http_body(url, opener) or ""
    return "", body


def proxy_ready() -> bool:
    opener = build_opener()
    for attempt in range(3):
        for method in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(
                    "https://mp.weixin.qq.com/",
                    headers={"User-Agent": UA},
                    method=method,
                )
                opener.open(req, timeout=10)
                return True
            except Exception:
                continue
        time.sleep(0.5 * (attempt + 1))
    return False


def enrich_pending(registry: dict[str, Any], *, limit: int | None = None) -> dict[str, int]:
    """给无标题条目抓标题，并打上 dev_related 标记。"""
    batch = limit or ENRICH_BATCH
    pending = [
        row
        for row in registry.get("items", {}).values()
        if not row.get("title")
        and row.get("status") in ("discovered", "title_failed")
        and url_has_sn(row.get("url", ""))
    ]
    pending.sort(key=lambda x: x.get("first_seen", ""), reverse=True)
    pending = pending[:batch]
    if not pending:
        return {"fetched": 0, "titles": 0, "failed": 0}

    opener = build_opener()
    titles = failed = 0
    for row in pending:
        title, body = fetch_title_from_page(row["url"], opener)
        if title:
            row["title"] = title
            row["status"] = "title_fetched"
            titles += 1
        else:
            row["status"] = "title_failed"
            failed += 1
        if body:
            row["body"] = body
            row["body_source"] = "HTTP抓取"
            row["status"] = "body_fetched"
        ok, reason = is_dev_related(
            row.get("title", ""),
            row.get("summary", ""),
            row.get("source_name", ""),
        )
        row["dev_related"] = ok
        row["filter_reason"] = reason
        row["fetched_at"] = _now()
        time.sleep(0.35)

    return {"fetched": len(pending), "titles": titles, "failed": failed}


def enrich_body_pending(registry: dict[str, Any], *, limit: int | None = None) -> dict[str, int]:
    """给已有 title + sn 但无正文的条目补 body。"""
    batch = limit or BODY_ENRICH_BATCH
    pending = [
        row
        for row in registry.get("items", {}).values()
        if row.get("title")
        and url_has_sn(row.get("url", ""))
        and len(row.get("body") or "") < 80
        and row.get("status") in ("title_fetched", "body_fetched", "discovered", "title_idb")
    ]
    pending.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
    pending = pending[:batch]
    if not pending:
        return {"fetched": 0, "bodies": 0, "failed": 0}

    opener = build_opener()
    bodies = failed = 0
    for row in pending:
        body = fetch_http_body(row["url"], opener)
        if len(body) > 80:
            row["body"] = body
            row["body_source"] = "HTTP抓取"
            row["status"] = "body_fetched"
            row["fetched_at"] = _now()
            bodies += 1
        else:
            failed += 1
        time.sleep(0.35)

    return {"fetched": len(pending), "bodies": bodies, "failed": failed}


def export_dev_corpus(registry: dict[str, Any]) -> dict[str, Any]:
    ensure_mp_scroll_dirs()
    ninjasin_keys = load_known_keys()
    items = []
    skipped_corpus_dup = 0
    for row in registry.get("items", {}).values():
        if not row.get("title"):
            continue
        ok, reason = is_dev_related(
            row.get("title", ""),
            row.get("summary", ""),
            row.get("source_name", ""),
        )
        if not ok:
            continue
        dup_probe = {
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "time": row.get("last_seen", ""),
        }
        if dedup_key(dup_probe) in ninjasin_keys:
            skipped_corpus_dup += 1
            continue
        body = row.get("body") or ""
        body_len = len(body)
        copy = dict(row)
        copy["filter_reason"] = reason
        copy["body_len"] = body_len
        copy["has_body"] = body_len >= 80
        copy.setdefault("url_kind", "full" if url_has_sn(row.get("url", "")) else "triple")
        items.append(copy)
    items.sort(key=lambda x: x.get("fetched_at") or x.get("last_seen", ""), reverse=True)

    with_body = sum(1 for i in items if i.get("has_body"))
    by_kind: dict[str, int] = {}
    for i in items:
        k = i.get("url_kind") or "unknown"
        by_kind[k] = by_kind.get(k, 0) + 1

    meta = {
        "exported_at": _now(),
        "source": "mp-scroll pipeline (IndexedDB watch + auto enrich)",
        "total_registry": len(registry.get("items", {})),
        "dev_kept": len(items),
        "dev_skipped_corpus_dup": skipped_corpus_dup,
        "dev_with_body": with_body,
        "dev_title_only": len(items) - with_body,
        "dev_by_url_kind": by_kind,
        "proxy": PROXY,
    }
    payload = {"meta": meta, "items": items}
    stamp = datetime.now().strftime("%Y-%m-%d")
    batch_dir = MP_SCROLL_ARCHIVE / stamp
    batch_dir.mkdir(parents=True, exist_ok=True)
    out_json = batch_dir / "mp_scroll_dev.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = MP_SCROLL_EXPORT / "mp_scroll_dev_latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    (MP_SCROLL_KB / "INDEX.md").write_text(
        "\n".join(
            [
                "# 公众号 · 滑列表语料（全自动）",
                "",
                f"- 最近导出: `{meta['exported_at']}`",
                f"- 注册表 URL: **{meta['total_registry']}**",
                f"- 开发向: **{meta['dev_kept']}**（相对已有语料去重跳过 **{meta.get('dev_skipped_corpus_dup', 0)}**）",
                f"- 有正文: **{meta['dev_with_body']}** / 仅标题: **{meta['dev_title_only']}**",
                f"- url_kind: {meta['dev_by_url_kind']}",
                f"- 注册表: [`../mp-capture/registry/idb_registry.json`](../mp-capture/registry/idb_registry.json)",
                f"- 快照: [`exports/mp_scroll_dev_latest.json`](exports/mp_scroll_dev_latest.json)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"dev_kept": len(items), "export_json": str(out_json)}


def run_pipeline(*, enrich: bool = True, enrich_limit: int | None = None, ocr: bool = False) -> dict[str, Any]:
    scan = scan_once(ocr=ocr)
    registry = load_registry()
    enrich_stats = {"fetched": 0, "titles": 0, "failed": 0, "skipped": False}
    body_stats = {"fetched": 0, "bodies": 0, "failed": 0, "skipped": False}
    if enrich:
        if proxy_ready():
            enrich_stats = enrich_pending(registry, limit=enrich_limit)
            body_stats = enrich_body_pending(registry, limit=enrich_limit)
            save_registry(registry)
        else:
            enrich_stats["skipped"] = True
            body_stats["skipped"] = True
    export_stats = export_dev_corpus(registry)
    return {"scan": scan, "enrich": enrich_stats, "body_enrich": body_stats, "export": export_stats}


# --- compatibility helpers used by mp_registry.py ---
def merge_urls(registry: dict[str, Any], urls: list[str], **kwargs: Any) -> list[str]:
    cards = [{"url": u, "title": "", "source_name": ""} for u in urls]
    return merge_cards(registry, cards, live_count=kwargs.get("live_count"))


def find_items(
    registry: dict[str, Any],
    query: str,
    *,
    only_new: bool = False,
    only_marked: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    items = list(registry.get("items", {}).values())
    if only_marked:
        items = [x for x in items if x.get("marked")]
    if only_new:
        items = [x for x in items if not x.get("title")]
    q = query.strip().lower()
    if q:
        matched = []
        for item in items:
            hay = " ".join(
                [
                    item.get("url", ""),
                    item.get("title", ""),
                    item.get("summary", ""),
                    item.get("source_name", ""),
                ]
            ).lower()
            if q in hay:
                matched.append(item)
        items = matched
    items.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
    return items[:limit]


def mark_items(registry: dict[str, Any], query: str) -> list[str]:
    matched = find_items(registry, query, limit=10_000)
    urls: list[str] = []
    for item in matched:
        item["marked"] = True
        urls.append(item["url"])
    return urls
