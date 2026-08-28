"""Cross-corpus dedup index (URL + title)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from paths import ARCHIVE_ROOT, CURATED_DIR, NINJASIN_STATE_DIR, WATCH_CONTACT, ensure_kb_dirs

PROCESSED_INDEX = NINJASIN_STATE_DIR / "processed_keys.json"


def norm_title(title: str) -> str:
    t = html_unescape(title or "")
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def html_unescape(text: str) -> str:
    import html

    return html.unescape(text)


def norm_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    u = u.split("#")[0]
    if "?" in u:
        base, qs = u.split("?", 1)
        keep = []
        for part in qs.split("&"):
            if part.startswith(("__biz=", "mid=", "idx=", "sn=", "chksm=")):
                keep.append(part)
        u = base + ("?" + "&".join(keep) if keep else "")
    return u


def dedup_key(item: dict) -> str:
    url = norm_url(str(item.get("url") or ""))
    if url and "mp.weixin.qq.com" in url:
        return f"url:{url}"
    title = norm_title(str(item.get("title") or ""))
    if len(title) >= 6:
        return f"title:{title}"
    return f"msg:{item.get('time', '')}:{title[:40]}"


def _iter_archive_items() -> list[dict]:
    items: list[dict] = []
    if not ARCHIVE_ROOT.is_dir():
        return items
    for path in ARCHIVE_ROOT.rglob("*.json"):
        if path.name not in ("delta.json", "delta_full.json"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        chunk = data.get("items", [])
        if isinstance(chunk, list):
            items.extend(chunk)
    return items


def _iter_curated_items() -> list[dict]:
    items: list[dict] = []
    curated = CURATED_DIR / f"{WATCH_CONTACT}_full_parsed.json"
    if not curated.is_file():
        legacy = list(CURATED_DIR.glob("*_full_parsed.json"))
        curated = legacy[0] if legacy else curated
    if not curated.is_file():
        return items
    try:
        data = json.loads(curated.read_text(encoding="utf-8"))
        items.extend(data.get("items", []))
    except (json.JSONDecodeError, OSError):
        pass
    return items


def load_known_keys(*, include_persisted: bool = True) -> set[str]:
    ensure_kb_dirs()
    keys: set[str] = set()
    for it in _iter_archive_items() + _iter_curated_items():
        keys.add(dedup_key(it))
    if include_persisted and PROCESSED_INDEX.is_file():
        try:
            data = json.loads(PROCESSED_INDEX.read_text(encoding="utf-8"))
            keys.update(data.get("keys", []))
        except (json.JSONDecodeError, OSError):
            pass
    return keys


def save_known_keys(keys: set[str]) -> None:
    ensure_kb_dirs()
    PROCESSED_INDEX.write_text(
        json.dumps({"keys": sorted(keys)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def split_new_items(items: list[dict], known: set[str] | None = None) -> tuple[list[dict], list[dict]]:
    known = known if known is not None else load_known_keys()
    net_new: list[dict] = []
    dups: list[dict] = []
    seen_run: set[str] = set()
    for it in items:
        key = dedup_key(it)
        if key in known or key in seen_run:
            dups.append(it)
            continue
        seen_run.add(key)
        net_new.append(it)
    return net_new, dups


def register_keys(items: list[dict], known: set[str] | None = None) -> set[str]:
    known = set(known or load_known_keys())
    for it in items:
        known.add(dedup_key(it))
    save_known_keys(known)
    return known
