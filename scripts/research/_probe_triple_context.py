"""Inspect triplekey neighborhood for sn/title fields."""
from __future__ import annotations

import re

from mp_capture.idb_reader import read_storage_bytes

text = read_storage_bytes().decode("utf-8", errors="replace")

for m in re.finditer(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"', text):
    key = m.group(1)
    if "2247485975" not in key and "2247489379" not in key:
        continue
    start = max(0, m.start() - 500)
    end = min(len(text), m.end() + 800)
    window = text[start:end]
    print("===", key, "===")
    # printable only
    printable = "".join(ch if ch.isprintable() or ch in "\n" else "." for ch in window)
    print(printable[:1200])
    print()
