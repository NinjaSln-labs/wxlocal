# 根目录文件清单与迁移动作

> 与 [REFACTOR_PLAN.md](REFACTOR_PLAN.md) 配套。  
> **图例**：✅ 已完成 · ⏳ 待办 · 🔀 shim · 🗑 删除 · 📦 迁包 · 📁 迁 scripts

**统计（2026-08-28 · v0.2.0）**：根目录 `.py` **0** · bat/vbs **≤12** · 实现全在 `wxlocal/` + `scripts/`

---

## Python — 原根 shim（R10 已删）

| 文件 | 实现位置 | 阶段 |
|------|----------|------|
| `watchdog.py` 等全部根 `.py` | 见 [CHANGELOG.md](../CHANGELOG.md) | R10 ✅ 🗑 |
| `mp_capture/` 根包 | `wxlocal/pipelines/mp_scroll/capture/` | R9–R10 ✅ |
| `wxlocal/_legacy.py` | 删除 | R10 ✅ 🗑 |

---

## Launchers（canonical）

| 文件 | 说明 |
|------|------|
| `run_chat_watch.bat` / `run_mp_scroll.bat` | `-m …bootstrap` via VBS |
| `run_extract.bat` / `run.bat` / `run_web.bat` | core / export / web |
| `run_mp_capture.bat` / `stop_mp_capture.bat` | mitm 可选 |
| `stop_wxlocal.bat` / `status_wxlocal.bat` | daemon_status |
| `setup_wxlocal_autostart.bat` / `WxLocalAutostart.vbs` | 登录自启 |
| `run-elevated.bat` | 提升权限入口 |

运维：`scripts/ops/reset_mp_scroll.py`（根 bat 已收口）。
