"""公众号推送 · 开发向过滤规则（默认读知识库 config，无则内置 fallback）。"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

from paths import MP_SCROLL_KB

_BUILTIN = {
    "dev_keywords": [
        "github", "open source", "llm", "gpt", "claude", "agent", "skill", "mcp",
        "代码", "编程", "开发", "python", "typescript", "架构", "模型", "arxiv",
    ],
    "block_keywords": ["外卖", "直播", "优惠", "营销"],
    "dev_source_hints": ["极客", "开发者", "github", "开源"],
}


@lru_cache(maxsize=1)
def _load_filter_config() -> dict:
    override = os.environ.get("WECHAT_DEV_FILTER_CONFIG", "").strip()
    candidates = []
    if override:
        candidates.append(Path(override))
    candidates.append(MP_SCROLL_KB / "config" / "dev_filter.json")
    for path in candidates:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                continue
    return _BUILTIN


def _lists(key: str) -> list[str]:
    val = _load_filter_config().get(key, [])
    return list(val) if isinstance(val, list) else []


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def is_dev_related(title: str, summary: str = "", source_name: str = "") -> tuple[bool, str]:
    """返回 (是否保留, 原因标签)。"""
    dev_keywords = _lists("dev_keywords")
    block_keywords = _lists("block_keywords")
    dev_source_hints = _lists("dev_source_hints")

    blob = _norm(f"{title} {summary} {source_name}")
    if len(blob) < 4:
        return False, "empty"

    dev_hits = [k for k in dev_keywords if k.lower() in blob]
    block_hits = [k for k in block_keywords if k in (title + summary + source_name)]
    source_dev = any(h in _norm(source_name) for h in dev_source_hints)

    if dev_hits:
        strong_dev = any(
            k in blob
            for k in (
                "github", "开源", "agent", "skill", "claude", "cursor", "llm",
                "代码", "编程", "开发", "api", "mcp", "架构", "模型", "arxiv",
                "python", "typescript", "devops", "coder", "程序员", "开发者",
            )
        )
        if block_hits and not strong_dev and len(dev_hits) < 2:
            return False, f"blocked:{block_hits[0]}"
        return True, f"dev:{dev_hits[0]}"

    if source_dev and not block_hits:
        return True, "source_hint"

    if block_hits:
        return False, f"blocked:{block_hits[0]}"

    return False, "no_match"
