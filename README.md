# wxlocal

Read and export **WeChat PC 4.x** local data on Windows: decrypt chats, scroll the subscription feed (IndexedDB), optional chat-watch export.

> **Maintained by [NinjaSin Labs](https://github.com/ninjasin-labs)** · self-learning / research only — see [DISCLAIMER](docs/DISCLAIMER.md).

> **Platform:** Windows · local `xwechat_files` only

## Features

| Module | Entry | What it does |
|--------|-------|--------------|
| **Core** | `run_extract.bat`, `app.py` | Decrypt local DB, export chats, Web UI |
| **mp-scroll** | `watch_mp_idb.py` | Scroll subscription feed → URL registry → enrich |
| **chat-watch** | `watchdog.py` | Auto-sync one contact when WeChat is logged in |
| **mp-capture** | `run_mp_capture.py` | Optional mitmproxy capture |

## Quick start

```powershell
git clone https://github.com/ninjasin-labs/wxlocal.git
cd wxlocal

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

copy .env.example .env
# Set WECHAT_DATA_ROOT

.\run_extract.bat
```

## Configuration

See [`.env.example`](.env.example). Knowledge-base exports go to `WECHAT_KB_ROOT` (default `./data/knowledge-base`).

## Docs

- [docs/DISCLAIMER.md](docs/DISCLAIMER.md) — **required reading**
- [docs/STANDALONE.md](docs/STANDALONE.md) — OSS layout
- [docs/MP_CAPTURE.md](docs/MP_CAPTURE.md) — mitm / IDB
- [docs/WECHAT_4.1.13_RESEARCH.md](docs/WECHAT_4.1.13_RESEARCH.md) — decryption notes

## License

MIT — see [LICENSE](LICENSE). Bundled [wcdb-key-tool](vendor/wcdb-key-tool-main/) (MIT).
