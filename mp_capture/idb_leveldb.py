"""LevelDB record-level triple+title extraction via chromium-reader (Windows-friendly)."""
from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

from mp_capture.idb_blink import (
    _merge_triple_card,
    _read_nick_from_chunk,
    extract_triple_keys_from_value,
    read_title_from_chunk,
)

MP_IDB_NAME = "https_mp.weixin.qq.com_0.indexeddb.leveldb"


def _mp_idb_dirs(storage_dirs: list[Path]) -> list[Path]:
    return [d for d in storage_dirs if d.name == MP_IDB_NAME or MP_IDB_NAME in d.as_posix()]


def _copy_leveldb_dir(src: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="mp-idb-ldb-"))
    for f in src.iterdir():
        if f.is_file() and f.name != "LOCK":
            shutil.copy2(f, tmp / f.name)
    return tmp


def extract_triple_cards_from_leveldb(idb_dir: Path, *, copy: bool = False) -> list[dict[str, str]]:
    """Parse live LevelDB records; prefer same-value triple+title pairing."""
    try:
        from chromium_reader.leveldb import KeyState, RawLevelDb
    except ImportError:
        return []

    if not idb_dir.is_dir():
        return []

    work = _copy_leveldb_dir(idb_dir) if copy else idb_dir
    merged: dict[str, dict[str, str]] = {}
    try:
        with RawLevelDb(str(work)) as db:
            for rec in db.iterate_records_raw():
                if rec.state != KeyState.LIVE:
                    continue
                val = rec.value or b""
                if b"triplekey" not in val:
                    continue
                title = read_title_from_chunk(val)
                nick = _read_nick_from_chunk(val)
                for triple in extract_triple_keys_from_value(val):
                    card = {
                        "triple": triple,
                        "title": title,
                        "source_name": nick or "idb:leveldb",
                    }
                    _merge_triple_card(merged, card)
    finally:
        if copy and work != idb_dir:
            shutil.rmtree(work, ignore_errors=True)
    return list(merged.values())


def extract_triple_cards_from_leveldb_dirs(
    storage_dirs: list[Path],
    *,
    copy: bool = False,
) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for idb_dir in _mp_idb_dirs(storage_dirs):
        for card in extract_triple_cards_from_leveldb(idb_dir, copy=copy):
            _merge_triple_card(merged, card)
    return list(merged.values())
