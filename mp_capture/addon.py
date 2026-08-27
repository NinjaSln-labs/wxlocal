"""mitmproxy addon：拦截微信 PC 订阅号 / 文章流量。"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mp_capture.constants import CAPTURE_HOSTS, HIGH_VALUE_PATH_RE
from mp_capture.parsers import extract_from_body, normalize_article_url
from mp_capture.storage import (
    append_flow_audit,
    load_store,
    merge_items,
    save_raw_flow,
    save_store,
)

SAVE_RAW = os.environ.get("MP_CAPTURE_RAW", "1") not in ("0", "false", "False")
VERBOSE = os.environ.get("MP_CAPTURE_VERBOSE", "1") not in ("0", "false", "False")
AUDIT_ALL = os.environ.get("MP_CAPTURE_AUDIT", "1") not in ("0", "false", "False")

_store = load_store()
_pending_save = 0


def _host_match(host: str) -> bool:
    host = (host or "").lower()
    return any(h in host for h in CAPTURE_HOSTS)


def _should_inspect(flow) -> bool:
    host = flow.request.host or ""
    if _host_match(host):
        return True
    url = flow.request.pretty_url or ""
    return "weixin.qq.com" in url or "qpic.cn" in url


def _is_high_value(flow) -> bool:
    path = flow.request.path or ""
    url = flow.request.pretty_url or ""
    return bool(HIGH_VALUE_PATH_RE.search(path) or HIGH_VALUE_PATH_RE.search(url))


def _flow_meta(flow) -> dict:
    body = flow.response.content or b"" if flow.response else b""
    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "method": flow.request.method,
        "host": flow.request.host,
        "path": flow.request.path[:200] if flow.request.path else "",
        "url": flow.request.pretty_url[:300] if flow.request.pretty_url else "",
        "status": flow.response.status_code if flow.response else None,
        "bytes": len(body),
        "ctype": flow.response.headers.get("content-type", "") if flow.response else "",
        "high_value": _is_high_value(flow),
    }


class WeChatMPCapture:
    def response(self, flow):
        global _store, _pending_save
        if not flow.response or not _should_inspect(flow):
            return

        meta = _flow_meta(flow)
        if AUDIT_ALL:
            append_flow_audit(meta)

        _store["flows_seen"] = int(_store.get("flows_seen", 0)) + 1
        body = flow.response.content or b""
        if not body:
            return

        ctype = meta["ctype"]
        page_url = flow.request.pretty_url if (flow.request.path or "").startswith("/s") else ""
        high = meta["high_value"]

        if SAVE_RAW and (high or len(body) < 500_000):
            save_raw_flow(flow.request.host, flow.request.path, body, ctype, force=high)

        items = extract_from_body(body, ctype, page_url)

        req_url = normalize_article_url(flow.request.pretty_url or "")
        if req_url:
            items.append(
                {
                    "title": "",
                    "url": req_url,
                    "summary": "",
                    "source_name": "",
                    "parse_path": "request.url",
                }
            )

        if not items:
            if VERBOSE and high:
                print(f"[mp-capture] audit {meta['host']}{meta['path'][:60]} ({meta['bytes']}b)")
            return

        added = merge_items(_store, items, meta)
        _pending_save += 1
        if _pending_save >= 1:
            save_store(_store)
            _pending_save = 0

        if VERBOSE:
            for it in items:
                title = (it.get("title") or it.get("url") or "")[:70]
                print(f"[mp-capture] +{added} | {title}")


addons = [WeChatMPCapture()]


def done():
    save_store(_store)
