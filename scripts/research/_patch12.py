import json
import re
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DELTA = Path(__file__).parent / "output" / "archive" / "2026-08-25-delta"
data = json.load(open(DELTA / "delta_full.json", encoding="utf-8"))
it = next(x for x in data["items"] if x["index"] == 12)
for url, label in [
    ("https://raw.githubusercontent.com/alchaincyf/huashu-excel/master/README.md", "huashu-excel README"),
    ("https://raw.githubusercontent.com/alchaincyf/huashu-excel/master/SKILL.md", "huashu-excel SKILL"),
]:
    raw = urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "curl"}), timeout=30
    ).read().decode("utf-8", "replace")
    (DELTA / "supplements" / (re.sub(r"[^\w.-]+", "_", label) + ".md")).write_text(raw, encoding="utf-8")
    it["body"] = (it.get("body") or "") + f"\n\n---\n【补充来源: {label}】\n{url}\n\n" + raw
    it["body_source"] = (it.get("body_source") or "") + " + " + label
    print(label, len(raw))

meta = data["meta"]
meta["body_fetched_at"] = datetime.now().isoformat(timespec="seconds")
meta["body_avg_len"] = int(sum(len(i.get("body") or "") for i in data["items"]) / 21)
meta["body_short"] = sum(1 for i in data["items"] if len(i.get("body") or "") < 400)
meta["body_rich"] = sum(1 for i in data["items"] if len(i.get("body") or "") >= 1500)
grouped = defaultdict(list)
for i in data["items"]:
    grouped[i["category"]].append(i)
data["by_category"] = dict(grouped)
json.dump(data, open(DELTA / "delta_full.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

lines = [
    "# NinjaSin 增量正文",
    "",
    f"- 抓取: {meta['body_fetched_at']}",
    f"- 平均 {meta['body_avg_len']} / 短 {meta['body_short']} / 富 {meta['body_rich']}",
    "",
]
for cat in sorted(grouped):
    lines.append(f"## {cat}（{len(grouped[cat])}）")
    lines.append("")
    for it2 in grouped[cat]:
        lines += [
            f"### [{it2['index']}] {it2['title']}",
            "",
            f"- **时间**: {it2.get('time', '')}",
            f"- **来源**: {it2.get('source_name', '')}",
            f"- **链接**: {it2.get('url', '')}",
            f"- **正文来源**: {it2.get('body_source', '')}",
            f"- **字数**: {len(it2.get('body') or '')}",
            "",
        ]
        if it2.get("summary"):
            lines += ["**卡片摘要:**", "", it2["summary"], ""]
        if it2.get("body"):
            lines += ["**正文:**", "", it2["body"], ""]
        lines += ["---", ""]
(DELTA / "delta_full.md").write_text("\n".join(lines), encoding="utf-8")

delta = json.load(open(DELTA / "delta.json", encoding="utf-8"))
delta["items"] = data["items"]
delta["by_category"] = dict(grouped)
for k in ("body_fetched_at", "body_ok", "body_avg_len", "body_short", "body_rich"):
    delta["meta"][k] = meta[k]
json.dump(delta, open(DELTA / "delta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print("avg", meta["body_avg_len"], "short", meta["body_short"], "rich", meta["body_rich"])
for i in data["items"]:
    n = len(i.get("body") or "")
    if n >= 1500:
        flag = "RICH"
    elif n >= 400:
        flag = "MID"
    else:
        flag = "SHORT"
    print(f"[{i['index']:2d}] {flag:5s} {n}")
