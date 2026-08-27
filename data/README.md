# Default data directory (standalone mode)

When `WECHAT_KB_ROOT` is not set and the legacy `F:\ext\knowledge-base` path does not exist,
exports and registries are written under:

```
data/knowledge-base/wechat/
├── ninjasin/      # chat watch exports + archive
├── mp-scroll/     # scroll-feed dev corpus
├── mp-capture/    # mitm / IDB registry
└── mp-dev/        # followed-account exports
```

Runtime logs and keys stay in `./output/` (gitignored).

Set `WECHAT_KB_ROOT` to use an external drive or shared corpus root.
