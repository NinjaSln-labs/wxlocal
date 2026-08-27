# Personal / date-bound batch scripts

One-off corpus migrations and enrich experiments. **Not part of the public pipeline.**

During OSS prep, ad-hoc scripts that referenced private contact names or fixed paths were removed from the repo root. Production entry points:

- `watch_mp_idb.py` — mp-scroll
- `watchdog.py` — chat-watch
- `archive_ninjasin_delta.py` — incremental archive

If you still need old batch scripts locally, recover them from your own backup or git history before the OSS cleanup.
