# Legacy / local-only scripts

Moved from repo root during refactor **R1**. Not part of the public pipeline.

| Pattern | Examples |
|---------|----------|
| Debug | `debug_*.py` |
| Old key scanners | `scan_keys.py`, `login_scan.py`, `test_*.py` |
| One-offs | `fetch_full_content.py`, `parse_merged.py`, `find_contact.py` |
| Scratch | `_check_*.py`, `_print_*.py`, `_sample_*.py` |

Production entry points remain at repo root (shims until **R4**):

- `watch_mp_idb.py` — mp-scroll
- `watchdog.py` — chat-watch
- `bootstrap_autostart.py` — login autostart

Recover deleted local scripts from git history before OSS cleanup if needed.
