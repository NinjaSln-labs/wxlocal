# Example: chat-watch knowledge-base profile

Optional setup: auto-export messages from **one pinned WeChat contact** into a categorized archive.

## Enable

```powershell
$env:WECHAT_WATCH_CONTACT = "YourPinnedContact"
python watchdog.py --once
```

## Pipeline

1. `watchdog.py` — decrypt + `export_contact.py`
2. `archive_ninjasin_delta.py` — parse app messages, classify, dedup (filename is legacy)
3. `ninjasin_dedup.py` — cross-corpus URL/title dedup (filename is legacy)

## Customize

- Classification rules: edit `RULES` in `archive_ninjasin_delta.py` (planned: external YAML).
- Cutoff timestamp: `CUTOFF` in the same file.
- Curated baseline: `{WECHAT_KB_ROOT}/wechat/chat-watch/curated/` (or legacy `ninjasin/`).

## Outputs

```
wechat/chat-watch/
├── exports/messages_<Contact>.json
├── archive/<date>/delta.json
└── state/chat_watch.log
```

Adjust contact name, rules, and paths for your own learning workflow.
