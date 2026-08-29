# wxlocal · OSS maintenance notes

> **GitHub:** [github.com/NinjaSln-labs/wxlocal](https://github.com/NinjaSln-labs/wxlocal)

## What this project is

**wxlocal** — Windows tooling for WeChat PC 4.x local data (self-learning / research only).

| Module | Entry | Purpose |
|--------|-------|---------|
| **Core** | `run_extract.bat`, `wxlocal-export`, `wxlocal-web` | Decrypt local DB, export chats, Web UI |
| **chat-watch** | `run_chat_watch.bat` / `wxlocal-watch` | Auto-sync one contact's messages |
| **mp-scroll** | `run_mp_scroll.bat` / `wxlocal-mp-scroll` | Subscription feed via IndexedDB |
| **mp-capture** | `run_mp_capture.bat` / `python -m wxlocal.pipelines.mp_scroll.capture.run` | Optional mitmproxy capture |

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
├── wxlocal/              # installable package (config, core, pipelines, ops, shared, web, export)
├── launchers/win/        # VBS bootstrap
├── scripts/              # verify, daemon_status, ops, research
├── vendor/wcdb-key-tool-main/
├── docs/                 # STANDALONE, ARCHITECTURE, REFACTOR_PLAN
├── examples/chat-watch/
├── run_chat_watch.bat    # canonical Windows entrypoints
├── run_mp_scroll.bat
└── output/               # runtime (gitignored): keys, logs, decrypt cache
```

Root directory has **0** `.py` files (v0.2.0). See [ARCHITECTURE.md](ARCHITECTURE.md) and [CHANGELOG.md](../CHANGELOG.md).

## Autostart

Login flow: `WxLocalAutostart.vbs` → `pythonw -m wxlocal.ops.bootstrap_autostart` (waits for `WECHAT_KB_ROOT` / `WECHAT_DATA_ROOT` drives) → spawns `-m wxlocal.pipelines.mp_scroll.bootstrap` + `-m wxlocal.pipelines.chat_watch.bootstrap`.

- Startup folder: **only** `WxLocalAutostart.vbs`（仓库路径在 `%LOCALAPPDATA%\wxlocal\install_root.txt`，勿再放 `*.path` 到 Startup，否则会弹“选择打开方式”）

- Install: `setup_wxlocal_autostart.bat`
- Logs: `output/autostart_launch.log`, `output/autostart_bootstrap_*.log`
- `WXLOCAL_PYTHON` in `.env` is used (VBS alone cannot read `.env`)

## Phase checklist

- [x] Local folder renamed to `E:\workspace\wxlocal\`
- [x] R0–R10 structure refactor (root `.py` = 0, package under `wxlocal/`)
