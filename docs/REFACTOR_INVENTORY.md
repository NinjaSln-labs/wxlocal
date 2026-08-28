# 根目录文件清单与迁移动作

> 与 [REFACTOR_PLAN.md](REFACTOR_PLAN.md) 配套。  
> **图例**：✅ 已完成 · ⏳ 待办 · 🔀 shim · 🗑 删除 · 📦 迁包 · 📁 迁 scripts

**统计（2026-08-28）**：根目录 `.py` **33** · bat/vbs/ps1 **~20**

---

## Python — shim（R10 删除）

| 文件 | 实现位置 | 阶段 |
|------|----------|------|
| `watchdog.py` 🔀 | `wxlocal.pipelines.chat_watch.daemon` | R10 🗑 |
| `watch_mp_idb.py` 🔀 | `wxlocal.pipelines.mp_scroll.daemon` | R10 🗑 |
| `app.py` 🔀 | `wxlocal.web.app` | R10 🗑 |
| `main.py` 🔀 | `wxlocal.export.cli` | R10 🗑 |
| `service.py` 🔀 | `wxlocal.web.service` | R10 🗑 |
| `config.py` 🔀 | `wxlocal.config.config` | R10 🗑 |
| `paths.py` 🔀 | `wxlocal.config.paths` | R10 🗑 |
| `env_loader.py` 🔀 | `wxlocal.config.env_loader` | R10 🗑 |
| `daemon_util.py` 🔀 | `wxlocal.shared.daemon` | R10 🗑 |
| `ninjasin_dedup.py` 🔀 | `wxlocal.shared.dedup` | R10 🗑 |
| `mp_dev_filter.py` 🔀 | `wxlocal.shared.mp_filter` | R10 🗑 |

---

## Python — core（R7 迁 `wxlocal/core/`）

| 文件 | 目标 | 阶段 |
|------|------|------|
| `wcdb_bridge.py` | `wxlocal/core/wcdb.py` | R7 📦 |
| `scan_keys_v41.py` | `wxlocal/core/keys.py` | R7 📦 |
| `decrypt_db.py` | `wxlocal/core/decrypt.py` | R7 📦 |
| `read_messages.py` | `wxlocal/core/messages.py` | R7 📦 |
| `key_parser.py` | `wxlocal/core/key_parser.py` | R7 📦 |
| `subprocess_win.py` | `wxlocal/core/subprocess_win.py` | R7 📦 |

---

## Python — chat-watch pipeline（R6/R8）

| 文件 | 目标 | 阶段 |
|------|------|------|
| `bootstrap_ninjasin_watch.py` 🔀 | → `bootstrap_chat_watch.py` | R6 ✅ |
| `archive_ninjasin_delta.py` | `wxlocal/pipelines/chat_watch/archive.py` | R8 📦 |
| `export_contact.py` | `wxlocal/pipelines/chat_watch/export.py` | R8 📦 |

---

## Python — mp-scroll / mp-capture（R6/R8/R9）

| 文件 | 目标 | 阶段 |
|------|------|------|
| `bootstrap_mp_watch.py` 🔀 | → `bootstrap_mp_scroll.py` | R6 ✅ |
| `run_mp_capture.py` | `wxlocal/pipelines/mp_capture/run.py` | R8 📦 |
| `mp_registry.py` | `wxlocal/export/mp_registry.py` | R8 📦 |
| `mp_capture/` 目录 | `wxlocal/pipelines/mp_scroll/capture/` 或保留 | R9 📦 |

---

## Python — export（R8 迁 `wxlocal/export/`）

| 文件 | 目标 | 阶段 |
|------|------|------|
| `export_messages.py` | `wxlocal/export/messages.py` | R8 📦 |
| `export_mp_dev.py` | `wxlocal/export/mp_dev.py` | R8 📦 |
| `export_mp_idb.py` | `wxlocal/export/mp_idb.py` | R8 📦 |
| `export_mp_capture.py` | `wxlocal/export/mp_capture.py` | R8 📦 |

---

## Python — autostart（R6 可选迁 `wxlocal/ops/`）

| 文件 | 目标 | 阶段 |
|------|------|------|
| `autostart_util.py` | `wxlocal/ops/autostart.py` | R6 或 R8 📦 |
| `bootstrap_autostart.py` | `wxlocal/ops/bootstrap_autostart.py` | R6 或 R8 📦 |

---

## Python — 运维工具（R8 迁 `scripts/ops/`）

| 文件 | 目标 | 阶段 |
|------|------|------|
| `enrich_bodies_batch.py` | `scripts/ops/enrich_bodies_batch.py` | R8 📁 |
| `rescan_titles.py` | `scripts/ops/rescan_titles.py` | R8 📁 |
| `reset_mp_scroll.py` | `scripts/ops/reset_mp_scroll.py` | R8 📁 |
| `restore_idb_backup.py` | `scripts/ops/restore_idb_backup.py` | R8 📁 |
| `mp_capture_status.py` | `scripts/ops/mp_capture_status.py` | R8 📁 |

---

## Launchers — 保留（canonical）

| 文件 | 说明 |
|------|------|
| `run_extract.bat` | Core 解密 |
| `run_web.bat` | Web UI |
| `run_chat_watch.bat` | chat-watch |
| `run_mp_scroll.bat` | mp-scroll |
| `run_mp_capture.bat` | mitm 可选 |
| `stop_wxlocal.bat` | 统一 stop |
| `status_wxlocal.bat` | 统一 status |
| `setup_wxlocal_autostart.bat` | 自启安装 |
| `WxLocalAutostart.vbs` | 登录入口 |
| `launchers/win/run_daemon.vbs` | 共享 VBS |

---

## Launchers — R6 删除

| 文件 | 替代 |
|------|------|
| `run_ninjasin_watchdog.vbs` 🗑 | `run_chat_watch.bat` | R6 ✅ |
| `run_mp_idb_watch.vbs` 🗑 | `run_mp_scroll.bat` | R6 ✅ |
| `stop_ninjasin_watchdog.bat` 🗑 | `stop_wxlocal.bat` | R6 ✅ |
| `stop_mp_idb_watch.bat` 🗑 | `stop_wxlocal.bat` | R6 ✅ |
| `status_mp_idb_watch.bat` 🗑 | `status_wxlocal.bat` | R6 ✅ |

---

## Launchers — R10 删除 / 评估

| 文件 | 动作 |
|------|------|
| `WeChatReaderAutostart.vbs` | R10 🗑（已转发 WxLocal） |
| `setup_autostart.ps1` | 评估是否仍需要 |
| `run.bat` / `run-elevated.bat` | 合并进 `run_extract.bat` 或 📁 scripts |
| `reset_mp_scroll.bat` | 保留或改为 `scripts/ops` 包装 |

---

## 已在正确位置 ✅

| 路径 | 说明 |
|------|------|
| `wxlocal/` | 主包（R4/R5 已建） |
| `scripts/daemon_status.py` | stop/status |
| `scripts/verify.ps1` | 门禁 |
| `scripts/print_env.py`, `resolve_db_storage.py` | ops |
| `scripts/research/` | 51 probes，不动 |
| `scripts/legacy/` | R1 已迁 debug |
| `tests/` | pytest |
| `vendor/wcdb-key-tool-main/` | 第三方 |

---

## 根目录 `.py` 数量追踪

| 里程碑 | 根 `.py` 数 | 备注 |
|--------|-------------|------|
| R1 后 | ~25 | 垃圾已迁 |
| R5 后 | **33** | shim + 未迁 core/export |
| R8 后（目标） | ~12 | 仅 shim |
| R10 后（目标） | **0** | 全删 shim |
