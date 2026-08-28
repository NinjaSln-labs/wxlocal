# Changelog

## 0.2.0 — 2026-08-28

Breaking cleanup of the repo root: all Python lives under `wxlocal/` (and `scripts/`).

### Removed (use package / console scripts instead)

| Old root entry | Replacement |
|----------------|-------------|
| `watchdog.py` | `wxlocal-watch` / `python -m wxlocal.pipelines.chat_watch.daemon` |
| `watch_mp_idb.py` | `wxlocal-mp-scroll` / `python -m wxlocal.pipelines.mp_scroll.daemon` |
| `bootstrap_chat_watch.py` | `python -m wxlocal.pipelines.chat_watch.bootstrap` |
| `bootstrap_mp_scroll.py` | `python -m wxlocal.pipelines.mp_scroll.bootstrap` |
| `bootstrap_autostart.py` | `python -m wxlocal.ops.bootstrap_autostart` |
| `main.py` / `app.py` / `service.py` | `wxlocal-export` / `wxlocal-web` |
| `paths.py` / `config.py` / `env_loader.py` | `wxlocal.config.*` |
| `wcdb_bridge.py` / `decrypt_db.py` / … | `wxlocal.core.*` |
| `export_*.py` / `archive_*.py` | `wxlocal.export.*` / `wxlocal.pipelines.chat_watch.*` |
| `mp_capture/` package at repo root | `wxlocal.pipelines.mp_scroll.capture` |
| `WeChatReaderAutostart.vbs` / `setup_autostart.ps1` | `WxLocalAutostart.vbs` / `setup_wxlocal_autostart.bat` |
| `wxlocal/_legacy.py` | removed (no longer needed) |

### Launchers

- `run_chat_watch.bat` / `run_mp_scroll.bat` invoke `pythonw -m …bootstrap`
- `WxLocalAutostart.vbs` runs `-m wxlocal.ops.bootstrap_autostart`

### Keep

- Root `.bat` / `.vbs` / `.ps1` launchers
- `scripts/ops/` maintenance tools
- Optional OCR extra: `pip install "wxlocal[ocr]"`
