import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = json.load(open(Path("output/archive/2026-08-25-delta/delta_full.json"), encoding="utf-8"))


def quality(it):
    body = it.get("body") or ""
    summary = it.get("summary") or ""
    src = it.get("body_source") or ""
    native = body.split("【补充来源:")[0].split("【封面OCR】")[0]
    clean = re.sub(r"关闭更多|赞赏作者|写留言|已关注赞分享|最低赞赏|名称已清空|微信扫一扫", "", native)
    clean = re.sub(r"\s+", " ", clean).strip()

    has_project_ext = any(
        k in src or k in body[:2000]
        for k in (
            "README",
            "arXiv",
            "Fowler",
            "Paseo",
            "OpenViking",
            "Stitch",
            "Graphify",
            "Resource2Skill",
            "Agent-Reach",
            "reverse-skill",
            "huashu",
            "DeepSpec",
            "prime-rl",
            "Mojo",
            "Atypica",
            "Tezign",
            "MoE",
            "Grok Build",
            "PortSwigger",
            "HackerOne",
            "KV Cache",
            "Crawl4AI",
            "Firecrawl",
            "Mixtral",
            "HuggingFace",
        )
    )
    multi_ocr = "多图OCR" in src or "【多图OCR】" in body
    ocr_block = ""
    if "【多图OCR】" in body:
        ocr_block = body.split("【多图OCR】", 1)[1][:8000]
    ocr_clean = re.sub(r"\s+", " ", ocr_block).strip() if ocr_block else ""

    # Key info: what a reader needs from the share
    # - product/tool shares: name + what it does + how to get it (card des often enough; README is bonus)
    # - deep articles: need more than card
    title = it.get("title") or ""

    if has_project_ext and len(body) > 2500:
        if multi_ocr and len(ocr_clean) >= 800:
            return "A", "关键信息齐（卡片+外链+多图OCR）"
        return "A", "关键信息齐（卡片+项目/论文原文）"
    if multi_ocr and len(ocr_clean) >= 1200 and len(summary) >= 150:
        return "A", "关键信息齐（卡片+多图讲解OCR）"
    if multi_ocr and len(ocr_clean) >= 600:
        return "B", "基本齐（多图OCR补了展开；外链/卡片仍可跟）"
    if len(summary) >= 350 and ("完整卡片des" in src or len(summary) >= 350):
        # card des on image posts IS the authored text summary NinjaSin shared
        if has_project_ext:
            return "A", "关键信息齐（完整卡片+外链）"
        return "B", "关键信息基本齐（完整卡片文案；图文帖无独立长文）"
    if len(summary) >= 200 and has_project_ext:
        return "A", "关键信息齐（卡片+外链）"
    if len(summary) >= 200:
        return "B", "有完整卡片要点；缺图内细节/长文"
    if len(clean) >= 150:
        return "C", "仅短摘要，关键细节不足"
    return "D", "几乎无有效正文"


print("#  | 档 | 卡des | 总长 | 标题 | 说明")
print("---")
counts = {"A": 0, "B": 0, "C": 0, "D": 0}
for it in d["items"]:
    grade, note = quality(it)
    counts[grade] += 1
    print(
        f"[{it['index']:02d}] {grade}  des={len(it.get('summary') or ''):4d}  "
        f"body={len(it.get('body') or ''):5d}  {it['title'][:40]}"
    )
    print(f"     → {note}")
    print(f"     src: {(it.get('body_source') or '')[:100]}")

print("---")
print(f"A(齐)={counts['A']}  B(基本齐)={counts['B']}  C(不足)={counts['C']}  D(几乎无)={counts['D']}")
print(f"关键信息可用(A+B)={counts['A']+counts['B']}/21")
