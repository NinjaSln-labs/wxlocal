# wxlocal 开发计划

> **工作流**：先写计划 → 实现 → **本地验证通过** → 再 commit/push。  
> 每次交付须附「测试记录」：命令 + 退出码 + 关键输出一行。

---

## 验证门禁（每次提交前必跑）

| # | 命令 | 通过标准 |
|---|------|----------|
| T1 | `python -m compileall -q mp_capture paths.py config.py env_loader.py watchdog.py watch_mp_idb.py` | exit 0 |
| T2 | `python watchdog.py --once` | exit 0；解密目录为 `output/decrypted` |
| T3 | `python watch_mp_idb.py --once` | exit 0；写出 dev export |
| T4 | README 文档链接 | `docs/*.md` 所列文件均存在 |
| T5 | `pytest tests/`（待建） | exit 0；无网络/无微信进程依赖 |

**2026-08-27 记录（README + About）：**

```
T1 compileall OK
T2 watchdog --once OK (288 msgs, archive delta)
T3 watch_mp_idb --once OK (dev_kept=292)
T4 doc links OK
```

---

## Phase A — 文档与仓库门面 ✅

| 项 | 状态 | 验收 |
|----|------|------|
| README 对齐 qingfu/jinteng 格式 | ✅ | 人工审阅结构 |
| GitHub About + topics | ✅ | `gh repo view` |
| pyproject description 对齐 | ✅ | 与 About 一致 |

---

## Phase B — 测试基建 ✅

**目标**：CI 不只 `compileall`，增加无外部依赖的 smoke。

| 项 | 状态 | 验收 |
|----|------|------|
| B1 `tests/test_paths.py` | ✅ | `ensure_decrypted_dir()` legacy → canonical |
| B2 `tests/test_config.py` | ✅ | `.env.example` 键在 runtime 文件中有引用 |
| B3 CI 加 `pytest tests/` | ✅ | GitHub Actions |
| B4 `scripts/verify.ps1` | ✅ | 一键 T1–T5（`-SkipIntegration` 跳过 T2/T3） |

**2026-08-27 记录（Phase B）：**

```
T1 compileall OK
T5 pytest 4 passed
T2/T3 --once OK (local integration)
T4 doc links OK
```

**不做**：依赖真实 `WECHAT_DATA_ROOT` / 微信进程的集成测试进 CI（仅本地 `--once` 手测）。

---

## Phase C — 代码质量 ✅

| 项 | 状态 | 验收 |
|----|------|------|
| C1 daemon 公共逻辑抽取 | ✅ | `daemon_util.py` · T1–T3 通过 |
| C2 `run_extract.bat` 去硬编码 | ✅ | `.env` + `scripts/resolve_db_storage.py` |
| C3 清理 legacy `wechat-reader` 目录 | ⚠️ | 脚本已加固；`.venv` 被占用时需关 Cursor 后重跑 |

---

## Phase D — 运维与自启 ✅

| 项 | 状态 | 验收 |
|----|------|------|
| D1 `setup_autostart.ps1` 转发至 wxlocal 自启 | ✅ | 无矛盾说明 |
| D2 `status_wxlocal.bat` 显示两 daemon PID | ✅ | `scripts/daemon_status.py` |

**2026-08-27 记录（Phase C/D）：**

```
T1 compileall OK
T5 pytest 8 passed
T2/T3 --once OK
T4 doc links OK
```

---

## Phase R — 结构重构 ✅

详见 **[docs/REFACTOR_PLAN.md](REFACTOR_PLAN.md)** · 文件清单 **[docs/REFACTOR_INVENTORY.md](REFACTOR_INVENTORY.md)**

| 阶段 | 内容 | 状态 |
|------|------|------|
| R0 | 计划与清单 | ✅ |
| R1 | 根目录垃圾 → `scripts/legacy/` | ✅ |
| R2 | `wxlocal/shared` 打断反向依赖 | ✅ |
| R3 | 启动器合并 | ✅ |
| R4 | 包化 + console_scripts | ✅ |
| R5 | 命名收尾 + ARCHITECTURE | ✅ |

**Phase R — 完成**（详见 [REFACTOR_PLAN.md](REFACTOR_PLAN.md)、[ARCHITECTURE.md](ARCHITECTURE.md)）

## Phase E — wenjin 侧（非本仓，不处理）

| 项 | 说明 |
|----|------|
| E1 wenjin push remote | 用户决定时机 |
| E2 P-1 probe refresh | 见 wenjin HANDOFF |

---

## 提交清单模板

```
## 变更
- ...

## 测试
- [ ] T1 compileall
- [ ] T2 watchdog --once
- [ ] T3 watch_mp_idb --once
- [ ] T4 doc links
- [ ] T5 pytest（若已启用）

## 备注
（异常、跳过的项及原因）
```
