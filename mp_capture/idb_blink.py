"""WeChat IndexedDB Blink-style field parsing (mp.weixin.qq.com feed cards)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

TRIPLE_BIN_RE = re.compile(rb'triplekey"\x1d([\w=+-]+-\d{8,13}-\d+)"')
TRIPLE_TXT_RE = re.compile(r'triplekey"\s*([\w=+-]+-\d{8,13}-\d+)"')
# Structured IDB: triplekey"<RS>biz_mid_idx"  (<RS> = \x1d)
TRIPLE_IDB_RE = re.compile(rb'triplekey"\x1d([\w=+=-]+_\d+_\d+)')
TITLE_MARK = b"\x05title\x00c"
TITLE_DOT_MARK = b".title.c"
NICK_MARK = b"\x08nick_name"
# Pass 1: local window (fast, low false-positive risk).
CHUNK_RADIUS = 32000
# Pass 2: global nearest-title fallback (bytes in WAL; empirically up to ~74k).
NEAREST_MAX_DIST = 80000


def _score_text(s: str) -> int:
    if len(s) < 4:
        return 0
    good = sum(
        1
        for c in s
        if c.isascii() and c.isprintable() and c not in "\x00"
        or "\u4e00" <= c <= "\u9fff"
    )
    return good * 100 // max(len(s), 1)


def decode_utf16_le(data: bytes, max_chars: int = 300) -> str:
    end = min(len(data), max_chars * 2 + 2)
    for sep in (b"\x00\x00", b"\x22\x0e", b"\x22\x05", b"\x22\n", b"\x22\x0a"):
        i = data.find(sep)
        if 0 <= i < end:
            end = i
    raw = data[:end]
    if len(raw) % 2:
        raw = raw[:-1]
    return raw.decode("utf-16le", errors="ignore").strip()


def read_blink_string(data: bytes, marker: bytes) -> str:
    """Read UTF-16LE string after a Blink property marker."""
    pos = data.find(marker)
    if pos < 0:
        return ""
    raw = data[pos + len(marker) : pos + len(marker) + 900]
    best = ""
    best_score = 0
    for off in range(0, min(8, len(raw))):
        s = decode_utf16_le(raw[off:])
        s = re.split(r"title_gen_type|themeColor|coverFirst", s, maxsplit=1)[0].strip()
        sc = _score_text(s)
        if sc > best_score and len(s) >= 4 and sc >= 55:
            best_score = sc
            best = s
    return best


def normalize_triple_raw(raw: str) -> str:
    """Canonicalize triplekey to biz-mid-idx with hyphens."""
    raw = raw.strip()
    for sep in ("-", "_"):
        if sep not in raw:
            continue
        biz, mid, idx = raw.rsplit(sep, 2)
        if mid.isdigit() and idx.isdigit():
            return f"{biz}-{mid}-{idx}"
    return raw


def extract_triple_keys_from_value(data: bytes) -> list[str]:
    """Extract triplekey strings from a single LevelDB value or blob chunk."""
    seen: set[str] = set()
    out: list[str] = []
    text = data.decode("utf-8", "replace")

    def add(raw: str) -> None:
        norm = normalize_triple_raw(raw)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)

    for m in TRIPLE_IDB_RE.finditer(data):
        add(m.group(1).decode("utf-8", errors="ignore"))
    for m in TRIPLE_BIN_RE.finditer(data):
        add(m.group(1).decode())
    for t in TRIPLE_TXT_RE.findall(text):
        add(t)
    return out


def read_title_from_chunk(chunk: bytes) -> str:
    """Try Blink title markers in priority order."""
    for marker in (TITLE_MARK, TITLE_DOT_MARK):
        title = read_blink_string(chunk, marker)
        if title:
            return title
    return ""


def build_title_index(blob: bytes) -> list[tuple[int, str]]:
    """Scan entire blob once for all Blink title markers."""
    index: list[tuple[int, str]] = []
    pos = 0
    while True:
        i = blob.find(TITLE_MARK, pos)
        if i < 0:
            break
        window = blob[max(0, i - 200) : i + 1200]
        title = read_blink_string(window, TITLE_MARK)
        if not title:
            title = read_blink_string(window, TITLE_DOT_MARK)
        if title:
            index.append((i, title))
        pos = i + 1
    return index


def _title_markers_in_range(blob: bytes, start: int, end: int) -> list[int]:
    out: list[int] = []
    pos = max(0, start)
    end = min(len(blob), end)
    while pos < end:
        i = blob.find(TITLE_MARK, pos)
        if i < 0 or i >= end:
            break
        out.append(i)
        pos = i + 1
    return out


def _claim_nearest_marker(blob: bytes, triple_pos: int, chunk: bytes, chunk_start: int) -> int | None:
    """If chunk has a title, return the blob offset of the nearest title marker."""
    if not read_title_from_chunk(chunk):
        return None
    markers = _title_markers_in_range(blob, chunk_start, chunk_start + len(chunk))
    if not markers:
        return None
    return min(markers, key=lambda ti: abs(ti - triple_pos))


def _read_nick_from_chunk(chunk: bytes) -> str:
    nick = read_blink_string(chunk, NICK_MARK)
    if nick:
        return nick
    ni = chunk.find(NICK_MARK)
    if ni >= 0:
        raw = chunk[ni + len(NICK_MARK) : ni + len(NICK_MARK) + 120]
        m = re.match(rb'"([^"]{2,80})"', raw)
        if m:
            return m.group(1).decode("utf-8", errors="ignore")
    return ""


def split_object_chunks(blob: bytes) -> list[bytes]:
    """Split blob into approximate object chunks anchored at triplekey."""
    chunks: list[bytes] = []
    positions = [m.start() for m in TRIPLE_BIN_RE.finditer(blob)]
    if not positions:
        return [blob] if blob else []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(blob)
        start = max(0, pos - 10000)
        chunks.append(blob[start:end])
    return chunks


def extract_triple_cards(blob: bytes) -> list[dict[str, str]]:
    """Extract recommendation feed cards (triplekey + title + nick) from IDB blob."""
    text = blob.decode("utf-8", errors="replace")
    positions: list[tuple[int, str]] = []
    for m in TRIPLE_BIN_RE.finditer(blob):
        positions.append((m.start(), m.group(1).decode()))
    if not positions:
        for t in TRIPLE_TXT_RE.findall(text):
            p = text.find(f'triplekey"{t}"')
            if p >= 0:
                positions.append((p, t))

    by_triple: dict[str, dict[str, str]] = {}
    title_index = build_title_index(blob)
    used_title_pos: set[int] = set()

    # Pass 1: fixed window; claim title markers matched locally.
    for pos, triple in positions:
        start = max(0, pos - CHUNK_RADIUS)
        chunk = blob[start : min(len(blob), pos + CHUNK_RADIUS)]
        title = read_title_from_chunk(chunk)
        claimed = _claim_nearest_marker(blob, pos, chunk, start)
        if claimed is not None:
            used_title_pos.add(claimed)
        nick = _read_nick_from_chunk(chunk)
        prev = by_triple.get(triple)
        if prev is None:
            by_triple[triple] = {
                "triple": triple,
                "title": title,
                "source_name": nick or "idb:triplekey",
            }
        else:
            if title and not prev.get("title"):
                prev["title"] = title
            if nick and prev.get("source_name") == "idb:triplekey":
                prev["source_name"] = nick

    # Pass 2: nearest unused title marker for triples still missing title.
    missing = {t for t, c in by_triple.items() if not c.get("title")}
    if missing and title_index:
        candidates: list[tuple[int, str, int, str, int]] = []
        for pos, triple in positions:
            if triple not in missing:
                continue
            for ti, title in title_index:
                if ti in used_title_pos:
                    continue
                dist = abs(ti - pos)
                if dist <= NEAREST_MAX_DIST:
                    candidates.append((dist, triple, ti, title, pos))
        candidates.sort(key=lambda x: x[0])
        assigned_triples: set[str] = set()
        for dist, triple, ti, title, _pos in candidates:
            if triple in assigned_triples or ti in used_title_pos:
                continue
            assigned_triples.add(triple)
            used_title_pos.add(ti)
            by_triple[triple]["title"] = title

    return list(by_triple.values())


def iter_leveldb_data_files(store_dir: Path) -> Iterator[tuple[Path, bytes]]:
    """Yield (.log/.ldb) payloads one file at a time — avoids cross-file distance artifacts."""
    if not store_dir.is_dir():
        return
    for file in sorted(store_dir.iterdir()):
        if not file.is_file() or file.name == "LOCK":
            continue
        if file.suffix not in (".log", ".ldb") and file.name not in ("LOG", "LOG.old"):
            continue
        try:
            data = file.read_bytes()
        except OSError:
            continue
        if data:
            yield file, data


def _merge_triple_card(merged: dict[str, dict[str, str]], card: dict[str, str]) -> None:
    triple = card["triple"]
    prev = merged.get(triple)
    if prev is None:
        merged[triple] = dict(card)
        return
    new_title = card.get("title") or ""
    old_title = prev.get("title") or ""
    if new_title and (not old_title or len(new_title) > len(old_title)):
        prev["title"] = new_title
    src = card.get("source_name") or ""
    if src and src != "idb:triplekey":
        prev["source_name"] = src


def extract_triple_cards_from_storage(storage_dirs: list[Path]) -> list[dict[str, str]]:
    """Scan each LevelDB file independently, then merge by triplekey."""
    merged: dict[str, dict[str, str]] = {}
    for store in storage_dirs:
        for _file, data in iter_leveldb_data_files(store):
            for card in extract_triple_cards(data):
                _merge_triple_card(merged, card)
    return list(merged.values())
