# Example: chat-watch knowledge-base profile

Optional setup: auto-export messages from **one pinned WeChat contact** into a categorized archive.

## Enable

```powershell
$env:WECHAT_WATCH_CONTACT = "YourPinnedContact"
wxlocal-watch --once
# or: python -m wxlocal.pipelines.chat_watch.daemon --once
```

## Pipeline

1. `wxlocal.pipelines.chat_watch.daemon` — decrypt + contact export
2. `wxlocal.pipelines.chat_watch.archive` — parse app messages, classify, dedup
3. `wxlocal.shared.dedup` — cross-corpus URL/title dedup

## Customize

- Classification rules: `archive_rules.json` under KB (see `wxlocal.pipelines.chat_watch.archive`)
- Cutoff timestamp: same config / env
- Curated baseline: `{WECHAT_KB_ROOT}/wechat/chat-watch/curated/` (or legacy `ninjasin/`)

## Outputs

```
wechat/chat-watch/
├── exports/messages_<Contact>.json
├── archive/<date>/delta.json
└── state/chat_watch.log
```

Adjust contact name, rules, and paths for your own learning workflow.
