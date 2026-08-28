# wxlocal · OSS maintenance notes

> **GitHub:** [github.com/NinjaSln-labs/wxlocal](https://github.com/NinjaSln-labs/wxlocal)

## What this project is

**wxlocal** — Windows tooling for WeChat PC 4.x local data (self-learning / research only).

| Module | Entry | Purpose |
|--------|-------|---------|
| **Core** | `run_extract.bat`, `app.py` | Decrypt local DB, export chats, Web UI |
| **chat-watch** | `run_chat_watch.bat` / `wxlocal-watch` / `watchdog.py` | Auto-sync one contact's messages |
| **mp-scroll** | `run_mp_scroll.bat` / `wxlocal-mp-scroll` / `watch_mp_idb.py` | Subscription feed via IndexedDB |
| **mp-capture** | `run_mp_capture.py` | Optional mitmproxy capture |

See [DISCLAIMER.md](DISCLAIMER.md) before publishing or using.

## Configuration (env-based)

| Variable | Default | Description |
|----------|---------|-------------|
| `WECHAT_DATA_ROOT` | (required) | `xwechat_files` path |
| `WECHAT_KB_ROOT` | `./data/knowledge-base` | Export / registry root |
| `WECHAT_WATCH_CONTACT` | `FileTransfer` | chat-watch contact |
| `WXLOCAL_PYTHON` | `.venv` pythonw | Silent launcher Python |

Filter / archive rules can live in consumer KB (`config/*.json`) — see downstream integrators.

## Repository layout

```
wxlocal/
├── wxlocal/              # installable package (config, pipelines, shared, web, export)
├── mp_capture/           # IndexedDB / OCR / registry
├── launchers/win/        # VBS bootstrap
├── scripts/              # verify, daemon_status, ops
├── vendor/wcdb-key-tool-main/
├── docs/                 # STANDALONE, ARCHITECTURE, REFACTOR_PLAN
├── examples/chat-watch/
├── run_chat_watch.bat    # canonical Windows entrypoints
├── run_mp_scroll.bat
└── output/               # runtime (gitignored): keys, logs, decrypt cache
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for module dependencies.

## Autostart

Login flow: `WxLocalAutostart.vbs` → `bootstrap_autostart.py` (waits for `WECHAT_KB_ROOT` / `WECHAT_DATA_ROOT` drives) → spawns `bootstrap_mp_watch.py` + `bootstrap_ninjasin_watch.py`.

- Startup folder: `WxLocalAutostart.vbs` + `wxlocal.path`
- Install: `setup_wxlocal_autostart.bat`
- Logs: `output/autostart_launch.log`, `output/autostart_bootstrap_*.log`
- `WXLOCAL_PYTHON` in `.env` is used (VBS alone cannot read `.env`)

Legacy `WeChatReaderAutostart.vbs` / `wechat-reader.path` supported during migration.

## Phase checklist

- [x] Local folder renamed to `E:\workspace\wxlocal\`
- [x] `git init`, push to github.com/NinjaSln-labs/wxlocal
- [x] GitHub CI: compileall
