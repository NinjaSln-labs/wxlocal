# Research scripts

One-off probes used while reverse-engineering WeChat PC 4.x IndexedDB / LevelDB / feed storage.

- **Not part of the production pipeline** — safe to ignore for normal use.
- Moved from repo root during OSS prep.
- Some files may still contain **stale local paths from development**; edit or set `WECHAT_RADIUM_PROFILES` before running.
- Outputs should go to `scripts/research/output/` (gitignored).

Run from repo root:

```powershell
.\.venv\Scripts\python.exe scripts\research\_probe_idb_scroll.py
```

**Do not publish** raw script outputs — they may contain private chat or account metadata.
