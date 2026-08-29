# HANDOFF 归档 · 已修坑

> 正文 [HANDOFF.md](../HANDOFF.md) §4 只保留仍会踩的项；确认已修写入此处。

## pits

| 日期 | 摘要 | 修复 |
|------|------|------|
| 2026-08-28 | 登录弹「选择打开方式」：Startup 里有 `wxlocal.path` | [b988d68] 根路径改 `%LOCALAPPDATA%\wxlocal\install_root.txt`；Startup 仅 VBS |
| 2026-08-28 | mp-scroll 重启后 `live=0`：默认 radium 用 LocalAppData，本机在 Roaming | [4b56bf3] `default_radium_profiles()` 优先已存在目录 |
| 2026-08-28 | chat-watch 有导出但今日 delta 变空：同日 `delta.json` 整文件覆盖 | [4b56bf3] 同日 merge；并恢复当日 4 条 |
| 2026-08-28 | CI `DATA_ROOT` 断言失败（无 `.env`） | [206f63b] 测试允许空字符串 |
| 2026-08-28 | R10 后 Startup 仍指向已删 `bootstrap_autostart.py` | 重跑 `setup_wxlocal_autostart.bat`；入口改为 `-m wxlocal.ops.bootstrap_autostart` |
| 2026-08-28 | C3 `E:\workspace\wechat-reader` 残留 | [24e8046] + `scripts/remove_legacy_wechat_reader_folder.ps1` |
