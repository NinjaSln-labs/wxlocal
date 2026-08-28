# 根目录文件清单与迁移动作

> 与 [REFACTOR_PLAN.md](REFACTOR_PLAN.md) 配套。  
> **图例**：✅ 已完成 · ⏳ 待办 · 🔀 shim · 🗑 删除 · 📦 迁包 · 📁 迁 scripts

**统计（2026-08-28 · v0.2.0+）**：根目录 `.py` **0** · bat/vbs **10** · 实现全在 `wxlocal/` + `scripts/`

---

## Python — 原根 shim（R10 已删）

| 文件 | 实现位置 | 阶段 |
|------|----------|------|
| `watchdog.py` 等全部根 `.py` | 见 [CHANGELOG.md](../CHANGELOG.md) | R10 ✅ 🗑 |
| `mp_capture/` 根包 | `wxlocal/pipelines/mp_scroll/capture/` | R9–R10 ✅ |
| `wxlocal/_legacy.py` | 删除 | R10 ✅ 🗑 |

---

## Launchers（canonical · 根目录）

| 文件 | 说明 |
|------|------|
| `run_chat_watch.bat` / `run_mp_scroll.bat` | `-m …bootstrap` via VBS |
| `run_extract.bat` / `run_web.bat` | core 解密导出 / Web UI |
| `run_mp_capture.bat` / `stop_mp_capture.bat` | mitm 可选 |
| `stop_wxlocal.bat` / `status_wxlocal.bat` | daemon_status |
| `setup_wxlocal_autostart.bat` (+ `.ps1`) / `WxLocalAutostart.vbs` | 登录自启 |

## 已收口（勿再放回根目录）

| 文件 | 去向 |
|------|------|
| `run.bat` / `run-elevated.bat` / `Run-AsAdmin.ps1` | 🗑（用 `run_extract.bat` / `wxlocal-export`） |
| `Read-WeChatChats.ps1` | `scripts/legacy/` |
| `reset_mp_scroll.bat` | `scripts/ops/reset_mp_scroll.py` |
| 空 `mp_capture/` 目录 | 🗑 |

运维：`scripts/ops/`。
