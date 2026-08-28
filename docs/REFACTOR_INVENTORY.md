# 根目录 Python 文件归类（R1 输入清单）

> 生成目的：重构 R1 迁移依据。生产入口在 R4 前保持原位。

## 生产 — daemon / bootstrap

| 文件 | 目标（R4） | R1 |
|------|-----------|-----|
| `watchdog.py` | `wxlocal.pipelines.chat_watch.daemon` | 留根 |
| `watch_mp_idb.py` | `wxlocal.pipelines.mp_scroll.daemon` | 留根 |
| `bootstrap_ninjasin_watch.py` | `wxlocal.pipelines.chat_watch.bootstrap` | 留根 |
| `bootstrap_mp_watch.py` | `wxlocal.pipelines.mp_scroll.bootstrap` | 留根 |
| `archive_ninjasin_delta.py` | `wxlocal.pipelines.chat_watch.archive` | 留根 |

## 生产 — export

| 文件 | 目标（R4） | R1 |
|------|-----------|-----|
| `export_contact.py` | `wxlocal.export.contact` | 留根 |
| `export_messages.py` | `wxlocal.export.messages` | 留根 |
| `export_mp_dev.py` | `wxlocal.export.mp_dev` | 留根 |
| `export_mp_idb.py` | `wxlocal.export.mp_idb` | 留根 |
| `export_mp_capture.py` | `wxlocal.export.mp_capture` | 留根 |

## 生产 — core / web / ops

| 文件 | 目标（R4） | R1 |
|------|-----------|-----|
| `main.py` | `wxlocal.cli` | 留根 |
| `app.py` | `wxlocal.web.app` | 留根 |
| `service.py` | `wxlocal.web.service` | 留根 |
| `config.py` | `wxlocal.config.settings` | 留根 |
| `paths.py` | `wxlocal.config.paths` | 留根 |
| `env_loader.py` | `wxlocal.config.env` | 留根 |
| `daemon_util.py` | `wxlocal.shared.daemon` | 留根（R2 抽 shared） |
| `wcdb_bridge.py` | `wxlocal.core.wcdb` | 留根 |
| `scan_keys_v41.py` | `wxlocal.core.keys` | 留根 |
| `decrypt_db.py` | `wxlocal.core.decrypt` | 留根 |
| `read_messages.py` | `wxlocal.core.messages` | 留根 |
| `key_parser.py` | `wxlocal.core.key_parser` | 留根 |
| `subprocess_win.py` | `wxlocal.core.subprocess_win` | 留根 |

## 生产 — shared（R2 优先抽取）

| 文件 | 目标 | R1 |
|------|------|-----|
| `ninjasin_dedup.py` | `wxlocal.shared.dedup` | 留根 → R2 抽 |
| `mp_dev_filter.py` | `wxlocal.shared.mp_filter` | 留根 → R2 抽 |

## 生产 — mp 工具脚本

| 文件 | 说明 | R1 |
|------|------|-----|
| `mp_registry.py` | CLI → idb_registry | 留根 |
| `mp_capture_status.py` | mitm 状态 | 留根 |
| `run_mp_capture.py` | mitm 启动 | 留根 |
| `enrich_bodies_batch.py` | 批处理补正文 | 留根 |
| `rescan_titles.py` | 标题重扫 | 留根 |
| `reset_mp_scroll.py` | 状态重置 | 留根 |
| `restore_idb_backup.py` | IDB 恢复 | 留根 |

## 迁至 `scripts/legacy/`（R1）

| 文件 | 原因 |
|------|------|
| `debug_layout.py`, `debug_name2id.py`, `debug_scan.py`–`debug_scan4.py` | 调试 |
| `scan_keys.py` | 旧版 scanner，硬编码路径 |
| `test_keys.py`, `test_keyinfo.py`, `test_passphrase.py` |  ad-hoc 测试 |
| `login_scan.py`, `fast_login_scan.py` | 密钥研究 |
| `check_dbs.py`, `extract_key_from_info.py`, `read_key_info.py` | 研究 |
| `fetch_full_content.py`, `find_contact.py`, `parse_merged.py` | 一次性 |
| `_check_delta_bodies.py`, `_print_delta.py`, `_sample_ocr.py` | 私有 scratch |

## 已在包内 / scripts

- `mp_capture/*` — R4 并入 `wxlocal.pipelines.mp_scroll` 或保留子包
- `scripts/research/*` — 不动
- `scripts/print_env.py`, `resolve_db_storage.py`, `daemon_status.py` — R3 可迁至 `scripts/ops/`
- `tests/*` — 不动
