"""Search IDB blob for missed article keywords."""
from __future__ import annotations

import re

from mp_capture.idb_reader import read_storage_bytes

blob = read_storage_bytes()
text = blob.decode("utf-8", errors="replace")

for mid in ("2247485975", "2247487435"):
    print(f"mid {mid} in blob:", mid in text)

for kw in ("SkillForge", "OpenObserve", "徐恪", "Eval", "虚拟机", "1008", "RING", "Vortex"):
    print(f"{kw} in blob:", kw in text)

urls = set(re.findall(r"https?://mp\.weixin\.qq\.com/s[^\s\"'\\<>]{10,400}", text))
print("urls", len(urls))
