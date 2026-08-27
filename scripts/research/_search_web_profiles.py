"""Search WeChat web profiles for opened article titles."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

PROFILES = __import__("paths").default_radium_profiles()
NEEDLES = [
    "虚拟机已困不住",
    "清华徐恪",
    "大模型安全不是给模型加个护栏",
    "从芯片到智能体的全链路",
]


def iter_blobs(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "LOCK":
            continue
        if path.suffix not in (".log", ".ldb", ".json", ".txt", ".html", ".js", ".css"):
            continue
        try:
            if path.stat().st_size > 8_000_000:
                continue
            yield path, path.read_bytes()
        except OSError:
            continue


def main() -> None:
    hits = []
    for path, blob in iter_blobs(PROFILES):
        text = blob.decode("utf-8", errors="replace")
        for needle in NEEDLES:
            if needle in text:
                hits.append((needle, path, path.stat().st_mtime))
    if not hits:
        print("no title hits in web profiles")
        return
    for needle, path, mtime in hits:
        print(needle)
        print(" ", path)
        print(" ", datetime.fromtimestamp(mtime))


if __name__ == "__main__":
    main()
