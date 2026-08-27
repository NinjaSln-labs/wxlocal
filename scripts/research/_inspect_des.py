"""对比消息 XML 中完整 des 与 archive summary；提取可能的图片相关字段"""
import html
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

msgs = json.load(open(Path("output/messages_NinjaSin.json"), encoding="utf-8"))["messages"]
delta = json.load(open(Path("output/archive/2026-08-25-delta/delta_full.json"), encoding="utf-8"))
cutoff = "2026-08-25 03:18:59"
new = [m for m in msgs if m.get("time", "") > cutoff]
print("new msgs", len(new))

def tag(xml, name):
    m = re.search(rf"<{name}>(.*?)</{name}>", xml, re.DOTALL)
    return html.unescape(m.group(1).strip()) if m else ""

for m in new:
    xml = m.get("content") or ""
    title = tag(xml, "title")
    des = tag(xml, "des")
    url = tag(xml, "url")
    # other interesting
    keys = sorted(set(re.findall(r"<([a-zA-Z0-9_]+)>", xml)))
    print(f"\n=== {m['time']} {title[:40]}")
    print(f"des_len={len(des)} keys={keys[:40]}")
    print(f"des_preview={des[:120]!r}")
    # match delta
    for it in delta["items"]:
        if it["title"][:20] == title[:20] or (it.get("url") and url and it["url"][:80] == url[:80]):
            print(f"delta#{it['index']} summary_len={len(it.get('summary') or '')} body_len={len(it.get('body') or '')}")
            if len(des) > len(it.get("summary") or ""):
                print("  *** des LONGER than summary ***")
            break
