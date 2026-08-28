"""Hex dump around .title.c markers in backup IDB."""
from __future__ import annotations

from pathlib import Path

from wxlocal.pipelines.mp_scroll.capture.idb_reader import read_storage_bytes

BACKUP = Path(
    r"F:\ext\knowledge-base\wechat\mp-scroll\reset-backup\20260827-151408\wechat-idb"
    r"\multitab_29adb3f5d489db767b94e00abb4cc4e4\https_mp.weixin.qq.com_0.indexeddb.leveldb"
)
MARKER = b".title.c"


def try_decode_title(raw: bytes) -> str:
    for off in range(0, 16):
        seg = raw[off:]
        # utf-16le until double null
        out = bytearray()
        i = 0
        while i + 1 < len(seg):
            if seg[i] == 0 and seg[i + 1] == 0:
                break
            out.extend(seg[i : i + 2])
            i += 2
        if len(out) >= 8:
            s = out.decode("utf-16le", errors="ignore").strip()
            if len(s) >= 6:
                return s
    return ""


def main() -> None:
    blob = read_storage_bytes([BACKUP])
    pos = 0
    shown = 0
    while shown < 8:
        i = blob.find(MARKER, pos)
        if i < 0:
            break
        raw = blob[i + len(MARKER) : i + len(MARKER) + 120]
        title = try_decode_title(raw)
        print(f"@{i} title={title!r}")
        print("hex:", raw[:40].hex())
        pos = i + len(MARKER)
        shown += 1


if __name__ == "__main__":
    main()
