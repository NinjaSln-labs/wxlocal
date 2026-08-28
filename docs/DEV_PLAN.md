# wxlocal 开发计划

> **工作流**：先写计划 → 实现 → **本地验证通过** → 再 commit/push。  
> 每次交付须附「测试记录」：命令 + 退出码 + 关键输出一行。

---

## 验证门禁（每次提交前必跑）

| # | 命令 | 通过标准 | 备注 |
|---|------|----------|------|
| T1 | `compileall` wxlocal + shims | exit 0 | |
| T5 | `pytest tests/` | exit 0 | **含 T0 同类：子进程 + 临时 `.env` 绑定断言** |
| T0 | `python scripts/check_env_binding.py` | exit 0 | 无微信；防 `load_env` 晚于常量绑定 |
| T2 | `wxlocal-watch --once` | exit 0 | 动 pipeline/config/**必跑**，勿长期 Skip |
| T3 | `wxlocal-mp-scroll --once` | exit 0 | 同上 |
| T4 | docs 链接存在 | exit 0 | |

一键：`.\scripts\verify.ps1`（`-SkipIntegration` 仅跳过 T2/T3，**不跳过 T0**）。

**R5 教训**：只跑 pytest 同进程断言挡不住「import 时读 env」回归；配置/paths 改动必须有**新进程 + 假 `.env`** 探针（现为 T0 / `tests/test_env_load_order.py`）。

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

## Phase R — 结构重构（R0–R5 ✅ · R6–R10 待实施）

详见 **[docs/REFACTOR_PLAN.md](REFACTOR_PLAN.md)** · 文件清单 **[docs/REFACTOR_INVENTORY.md](REFACTOR_INVENTORY.md)**

**Phase R0–R5 — 完成**（详见 [REFACTOR_PLAN.md](REFACTOR_PLAN.md)、[ARCHITECTURE.md](ARCHITECTURE.md)）

| 阶段 | 内容 | 状态 |
|------|------|------|
| R0 | 计划与清单 | ✅ |
| R1 | 根目录垃圾 → `scripts/legacy/` | ✅ |
| R2 | `wxlocal/shared` 打断反向依赖 | ✅ |
| R3 | 启动器合并 | ✅ |
| R4 | 包化 + console_scripts | ✅ |
| R5 | paths 拆分 + PID 命名 + ARCHITECTURE | ✅ |

---

## Phase R6–R10 — 根目录收口（待实施）

> 完整计划：[docs/REFACTOR_PLAN.md](REFACTOR_PLAN.md) · 文件级清单：[docs/REFACTOR_INVENTORY.md](REFACTOR_INVENTORY.md)

| 阶段 | 内容 | 优先级 | 状态 |
|------|------|--------|------|
| R6 | ninjasin/mp_idb 命名收敛 · bootstrap 迁包 · 删冗余 bat/vbs | P0 | ✅ |
| R7 | `wxlocal/core`（wcdb · decrypt · keys）· 去 `_legacy` | P0 | ⏳ |
| R8 | pipelines/export 迁包 · ops 脚本 → `scripts/ops/` | P1 | ⏳ |
| R9 | `mp_capture` 归位（可选） | P2 | ⏳ |
| R10 | 删根 shim · 根目录 0 `.py` · v0.2.0 | P1 | ⏳ |

**目标**：根目录只留 bat/vbs + 元数据；全部 Python 在 `wxlocal/` 内。

**最小可行**：R6 + R7（~4 天）即可消除 ninjasin 困惑并修好 pip 安装路径。

---

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
