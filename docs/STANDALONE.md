# wxlocal · OSS maintenance notes

> **GitHub:** [github.com/ninjasin-labs/wxlocal](https://github.com/ninjasin-labs/wxlocal)  
> **Org:** [NinjaSin Labs](https://github.com/ninjasin-labs)

## What this project is

**wxlocal** — Windows tooling for WeChat PC 4.x local data (self-learning / research only).

| Module | Entry | Purpose |
|--------|-------|---------|
| **Core** | `run_extract.bat`, `app.py` | Decrypt local DB, export chats, Web UI |
| **mp-scroll** | `watch_mp_idb.py` | Subscription feed via IndexedDB |
| **chat-watch** | `watchdog.py` | Auto-sync one contact's messages |
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
├── mp_capture/
├── vendor/wcdb-key-tool-main/
├── docs/
├── scripts/research/
├── examples/chat-watch/
└── paths.py
```

## Autostart

- `WxLocalAutostart.vbs` + Startup `wxlocal.path`
- `setup_wxlocal_autostart.ps1`

Legacy `WeChatReaderAutostart.vbs` / `wechat-reader.path` supported during migration.

## Phase checklist

- [x] Rename to wxlocal · ninjasin-labs
- [ ] `git init`, push to github.com/ninjasin-labs/wxlocal
- [ ] GitHub CI: compileall
