# Legacy / local-only scripts

Moved from repo root during refactor. Not part of the public pipeline.

| Pattern | Examples |
|---------|----------|
| Debug | `debug_*.py` |
| Old key scanners | `scan_keys.py`, `login_scan.py`, `test_*.py` |
| One-offs | `fetch_full_content.py`, `parse_merged.py`, `find_contact.py` |
| Scratch | `_check_*.py`, `_print_*.py`, `_sample_*.py` |

Production entry points (v0.2.0+): console scripts / `python -m wxlocal…` — see [CHANGELOG.md](../../CHANGELOG.md).

Recover deleted local scripts from git history if needed.
