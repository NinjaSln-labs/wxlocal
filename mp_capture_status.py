"""查看抓包状态。"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
EXPORT = Path(r"F:\ext\knowledge-base\wechat\mp-capture\exports")
RAW = Path(r"F:\ext\knowledge-base\wechat\mp-capture\raw")
AUDIT = EXPORT / "flow_audit.jsonl"
LATEST = EXPORT / "mp_capture_latest.json"


def main() -> None:
    print("=== mp-capture 状态 ===\n")

    if LATEST.is_file():
        data = json.loads(LATEST.read_text(encoding="utf-8"))
        print(f"已解析文章: {len(data.get('items', []))}")
        print(f"观测 flows: {data.get('flows_seen', 0)}")
        for it in data.get("items", [])[:8]:
            print(f"  - {it.get('title', '')[:65]}")
    else:
        print("尚无 mp_capture_latest.json")

    raw_n = len(list(RAW.glob("*.txt"))) if RAW.is_dir() else 0
    print(f"\nraw 文件: {raw_n}")

    if AUDIT.is_file():
        lines = AUDIT.read_text(encoding="utf-8").strip().splitlines()
        print(f"flow_audit 行数: {len(lines)}")
        hosts = Counter()
        paths = Counter()
        high = []
        for line in lines[-500:]:
            try:
                o = json.loads(line)
            except Exception:
                continue
            hosts[o.get("host", "")] += 1
            p = (o.get("path") or "")[:80]
            paths[p] += 1
            if o.get("high_value"):
                high.append(o)
        print("\n--- 主机 Top 8 ---")
        for h, n in hosts.most_common(8):
            print(f"  {n:4d}  {h}")
        print("\n--- 高价值请求 (最近) ---")
        if not high:
            print("  （尚无 /s /mp/ feed 类请求 — 推荐流 API 可能不走 HTTP 代理）")
        for o in high[-10:]:
            print(f"  {o.get('ts')} {o.get('host')}{o.get('path', '')[:70]} ({o.get('bytes')}b)")
    else:
        print("\nflow_audit.jsonl 尚无 — 请重启 run_mp_capture.bat（已增强审计）")

    print("\n提示: 代理已通若 raw>0 但无文章 → 在订阅号里【点开】文章正文，不要只刷列表")


if __name__ == "__main__":
    main()
