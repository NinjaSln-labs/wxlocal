"""Iterate WeChat mp IndexedDB LevelDB keys/values (offline copy)."""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

import plyvel

BACKUP = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)

TRIPLE_RE = re.compile(rb'triplekey"\x1d([\w=+-]+-\d{8,13}-\d+)"')
TRIPLE_RE2 = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')
TITLE_MARKER = b".title.c"


def decode_utf16_le_strings(data: bytes, min_len: int = 6) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(data) - 3:
        if data[i + 1] == 0 and (32 <= data[i] <= 126 or data[i] >= 128):
            j = i
            chars: list[str] = []
            while j < len(data) - 1 and data[j + 1] == 0:
                try:
                    chars.append(bytes([data[j], data[j + 1]]).decode("utf-16le"))
                except Exception:
                    break
                j += 2
            s = "".join(chars).strip()
            if len(s) >= min_len:
                out.append(s)
            i = max(i + 2, j)
        else:
            i += 1
    return out


def extract_title_from_value(val: bytes) -> str:
    # after .title.c marker try utf-16
    idx = val.find(TITLE_MARKER)
    if idx >= 0:
        raw = val[idx + len(TITLE_MARKER) : idx + len(TITLE_MARKER) + 600]
        for off in range(0, 12):
            seg = raw[off:]
            for s in decode_utf16_le_strings(seg, min_len=8):
                if any("\u4e00" <= c <= "\u9fff" for c in s) or "AI" in s.upper():
                    return s[:300]
    # fallback utf-16 scan whole value
    for s in decode_utf16_le_strings(val, min_len=10):
        if any("\u4e00" <= c <= "\u9fff" for c in s):
            if "triplekey" in s or "fontScale" in s:
                continue
            return s[:300]
    return ""


def main() -> None:
    if not BACKUP.is_dir():
        print("backup not found", BACKUP)
        sys.exit(1)

    tmp = Path(tempfile.mkdtemp(prefix="mp-idb-"))
    for f in BACKUP.iterdir():
        if f.is_file() and f.name != "LOCK":
            shutil.copy2(f, tmp / f.name)

    db = plyvel.DB(str(tmp), create_if_missing=False)
    triple_vals = 0
    title_vals = 0
    both = 0
    samples: list[tuple[str, str]] = []

    for key, val in db:
        has_triple = bool(TRIPLE_RE.search(val) or TRIPLE_RE2.search(val.decode("utf-8", "replace")))
        title = extract_title_from_value(val)
        has_title = bool(title)
        if has_triple:
            triple_vals += 1
        if has_title:
            title_vals += 1
        if has_triple and has_title:
            both += 1
            m = TRIPLE_RE.search(val) or TRIPLE_RE2.search(val.decode("utf-8", "replace"))
            tk = m.group(1).decode() if isinstance(m.group(1), bytes) else m.group(1)
            samples.append((tk, title))

    db.close()
    shutil.rmtree(tmp, ignore_errors=True)

    print(f"LevelDB entries scanned")
    print(f"  values with triplekey: {triple_vals}")
    print(f"  values with decodable title: {title_vals}")
    print(f"  values with BOTH: {both}")
    print("\nSamples (triple + title in same value):")
    for tk, title in samples[:15]:
        print(f"  {tk}")
        print(f"    -> {title[:80]}")


if __name__ == "__main__":
    main()
