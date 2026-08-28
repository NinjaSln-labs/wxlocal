# wxlocal 重构计划（完整版）

> **范围**：仅 `wxlocal` 本仓。  
> **工作流**：计划 → 实现 → `scripts/verify.ps1` → commit/push。  
> **原则**：小步交付、每步可回滚、旧入口 shim 保留 1 个 release 直至下一 minor/major。

---

## 0. 文档索引

| 文档 | 用途 |
|------|------|
| 本文 | 阶段划分、验收、风险 |
| [REFACTOR_INVENTORY.md](REFACTOR_INVENTORY.md) | 根目录每个文件的迁移动作 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 目标依赖与运行时结构 |
| [DEV_PLAN.md](DEV_PLAN.md) | 里程碑状态与测试门禁 |

---

## 1. 现状快照（R0–R5 已完成，2026-08-28）

### 1.1 已解决

| 问题 | 阶段 | 结果 |
|------|------|------|
| 调试脚本占根目录 | R1 | → `scripts/legacy/` |
| `mp_capture` 反向 import 根模块 | R2 | → `wxlocal/shared` |
| 33 个重复 launcher | R3 | → `launchers/win/run_daemon.vbs` + 规范 bat |
| 入口未包化 | R4 | → `wxlocal.*` + console_scripts |
| paths 单体、PID 命名混乱 | R5 | → `wxlocal/config/paths/*` + `chat_watch.pid` |

### 1.2 仍存在的问题

**根目录仍有 ~33 个 `.py`、~20 个 bat/vbs/ps1**（见 [REFACTOR_INVENTORY.md](REFACTOR_INVENTORY.md)）。

| 类别 | 数量 | 典型文件 | 原因 |
|------|------|----------|------|
| Shim（3–10 行） | 12 | `watchdog.py`, `paths.py`, `ninjasin_dedup.py` | R4 兼容层未删 |
| Core 未迁包 | 7 | `wcdb_bridge.py`, `decrypt_db.py`, `scan_keys_v41.py` | R4 只迁了入口 |
| Pipeline 逻辑留根 | 4 | `archive_ninjasin_delta.py`, `export_contact.py` | 未做 `pipelines.*` 子模块 |
| Export 留根 | 5 | `export_mp_dev.py`, `export_mp_idb.py` … | 未做 `wxlocal/export/*` |
| 运维/工具 | 6 | `enrich_bodies_batch.py`, `reset_mp_scroll.py` … | 未迁 `scripts/ops/` |
| Bootstrap 旧名 | 2 | `bootstrap_ninjasin_watch.py` | 自启链硬编码文件名 |
| mp_capture 独立顶栏包 | 1 目录 | `mp_capture/` | 未并入 `wxlocal.pipelines` |

**命名**：对外已是 chat-watch / mp-scroll；对内仍大量 `ninjasin_*`、`mp_idb_*`、wechat-reader 残留。

**依赖**：`wxlocal.pipelines` 经 `wxlocal._legacy` 仍 import 根目录 `export_contact`、`wcdb_bridge` 等；`pip install` 后靠 `sys.path` 补丁，非最终态。

### 1.3 目标终态（根目录）

```
wxlocal/                          # 仅保留用户-facing 入口
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── .env.example
│
├── run_extract.bat               # Core 一键解密
├── run_web.bat
├── run_chat_watch.bat
├── run_mp_scroll.bat
├── run_mp_capture.bat
├── stop_wxlocal.bat
├── status_wxlocal.bat
├── setup_wxlocal_autostart.bat
├── WxLocalAutostart.vbs
│
├── wxlocal/                      # 全部 Python 实现
├── launchers/win/
├── scripts/ops/ + scripts/research/ + scripts/legacy/
├── vendor/
├── tests/
├── docs/
├── templates/
└── output/                       # gitignore
```

**根目录 `.py` 目标：0 个**（或仅保留 `pyproject` 无关的 0；所有 py 在包内 + shims 在 `wxlocal/_shims/` 若必须）。

**过渡期**：允许 `WeChatReaderAutostart.vbs` 等 **最多 1 个 release** 的 deprecated 转发，之后删除。

---

## 2. 目标架构

### 2.1 包结构

```
wxlocal/
├── config/          env · paths（已完成）
├── core/            wcdb · decrypt · keys · messages · subprocess_win
├── shared/          dedup · filter · http · daemon（已完成）
├── pipelines/
│   ├── chat_watch/  daemon · bootstrap · archive · export_contact
│   └── mp_scroll/   daemon · bootstrap · registry 编排
├── export/          cli · contact · messages · mp_dev · mp_idb · mp_capture
├── web/             app · service（已完成）
├── ops/             autostart_util · bootstrap_autostart（可选）
└── _legacy.py       删除条件：无根目录 import 依赖
```

### 2.2 命名映射（一次性收敛）

| 旧（删除目标） | 新（canonical） |
|----------------|-----------------|
| `bootstrap_ninjasin_watch.py` | `wxlocal/pipelines/chat_watch/bootstrap.py` |
| `bootstrap_mp_watch.py` | `wxlocal/pipelines/mp_scroll/bootstrap.py` |
| `archive_ninjasin_delta.py` | `wxlocal/pipelines/chat_watch/archive.py` |
| `run_ninjasin_watchdog.vbs` | `launchers/win/run_chat_watch.vbs` 或删（bat 直调 VBS 参数） |
| `run_mp_idb_watch.vbs` | 同上 mp-scroll |
| `stop_ninjasin_watchdog.bat` | 删（仅保留 `stop_wxlocal.bat`） |
| `stop_mp_idb_watch.bat` | 删 |
| `status_mp_idb_watch.bat` | `status_wxlocal.bat mp-scroll` 或删 |
| `ninjasin_dedup.py` | 删 shim（只用 `wxlocal.shared.dedup`） |
| `NINJASIN_*` 常量 | 保留为 deprecated alias 1 release，文档标 `@deprecated` |
| KB 子目录 `wechat/ninjasin/` | 运行时只写 `chat-watch/`；读路径时 fallback（已有） |

### 2.3 依赖规则（强制）

1. `wxlocal.config` → 无业务依赖  
2. `wxlocal.core` → 仅 config  
3. `wxlocal.shared` → config  
4. `wxlocal.pipelines.*` / `wxlocal.export` → core + shared + config  
5. **禁止** 包内 `import export_contact` 等根模块  
6. **禁止** `mp_capture` import 根模块（已基本完成，R9 复核）  
7. `scripts/research` → 可 import `wxlocal`；反向禁止  

**验收**：`tests/test_imports.py` grep / import-linter；`wxlocal-watch --once` 在未把 repo root 加入 `PYTHONPATH` 时仍可用。

---

## 3. 分阶段实施

### 已完成：R0–R5 ✅

见 git history `1631d21` … `0518c5d`。摘要：

- R1 legacy 清扫 · R2 shared · R3 launchers · R4 包化入口 · R5 paths 拆分 + PID

---

### R6 — 命名收敛（ninjasin / mp_idb / wechat-reader）（2 天）✅

- `wxlocal/pipelines/*/bootstrap.py` — 真实逻辑
- 规范根入口：`bootstrap_chat_watch.py`、`bootstrap_mp_scroll.py`
- 旧名 `bootstrap_ninjasin_watch.py` / `bootstrap_mp_watch.py` 保留 shim
- 删除：`run_*_watchdog.vbs`、`stop_ninjasin_*`、`stop_mp_idb_*`、`status_mp_idb_watch.bat`
- `daemon_status.py` / 自启链已切到新名

---

### R7 — core 层包化（2–3 天）✅

- `wxlocal/core/{wcdb,keys,decrypt,messages,key_parser,subprocess_win}.py`
- 根目录对应文件保留 shim；`web`/`export`/`pipelines` 已改 `wxlocal.core.*`
- `tests/test_core_imports.py`；R8 后 chat-watch daemon 不再依赖 `_legacy` / 根 `export_contact`

---

### R8 — pipelines + export 包化（3–4 天）✅

- `wxlocal/pipelines/chat_watch/{export,archive}.py`
- `wxlocal/export/{messages,mp_dev,mp_idb,mp_capture_export,mp_registry}.py`
- `scripts/ops/` — enrich / rescan / reset / restore / mp_capture_status / run_mp_capture
- 根目录对应文件保留 shim；daemon 不再 `_legacy` / 根 `export_contact`

---

### R9 — mp_capture 归位（2–3 天，可选独立）✅

- 方案 A：`mp_capture/` → `wxlocal/pipelines/mp_scroll/capture/`
- 根 `mp_capture/*.py` 保留 shim；`run` 在 `capture/run.py`，ops 脚本转发
- 包内 / daemon / export / ops 改用 `wxlocal.pipelines.mp_scroll.capture.*`
- 研究脚本可继续 `import mp_capture`（shim）

---

### R10 — 删 shim、根目录收口（1–2 天）✅

- 根目录 `.py` = 0；`mp_capture/` shim 删除；`wxlocal/_legacy.py` 删除
- launcher 改为 `pythonw -m …`；`WeChatReaderAutostart.vbs` / `setup_autostart.ps1` 删除
- `pyproject.toml` → **0.2.0**；见根目录 `CHANGELOG.md`

---

## 4. 时间与优先级

| 阶段 | 工期 | 优先级 | 依赖 |
|------|------|--------|------|
| R6 命名 | 2d | **P0** | — |
| R7 core | 2–3d | **P0** | — |
| R8 pipelines/export | 3–4d | **P1** | R7 |
| R9 mp_capture | 2–3d | P2 | R8 |
| R10 删 shim | 1–2d | P1 | R7+R8 |

**合计**：约 **10–14 个工作日**。

**若时间紧（最小可行）**：**R6 + R7**（~4 天）→ 命名清晰 + pip install 不依赖根 path；shim 暂留。

---

## 5. 测试与门禁（每阶段）

| # | 命令 | 说明 |
|---|------|------|
| T1 | `python -m compileall -q wxlocal mp_capture` | 包内语法 |
| T2 | `wxlocal-watch --once` | chat-watch 集成 |
| T3 | `wxlocal-mp-scroll --once` | mp-scroll 集成 |
| T4 | doc links in `verify.ps1` | 文档存在 |
| T5 | `pytest tests/` | smoke |
| T6 | 自启手测（动 launchers 时） | 登录 → PID → stop |

**R7+ 新增**：

| # | 命令 | 说明 |
|---|------|------|
| T7 | `pip install -e . && wxlocal-watch --once`（cwd=/tmp 空目录） | 无 repo root path |

---

## 6. 风险与回滚

| 风险 | 缓解 |
|------|------|
| 自启文件名变更 | R6 先改 bootstrap 模块路径，VBS 参数化；保留旧 shim 1 release |
| Startup 文件夹旧 VBS | `setup_wxlocal_autostart.bat` 重装；文档说明 |
| 用户脚本 `import paths` | R10 前 CHANGELOG + shim；R10 major bump |
| KB 上旧 pid/log 文件名 | R5 已 migrate；R6 复核日志路径 |
| mp_capture 移动破坏 import | R9 方案 A 保留 shim 包 `mp_capture` → re-export |

**回滚**：每阶段单 commit；`git revert` 单步。

---

## 7. 刻意不做

- 微信解密算法 / vendor 内部  
- 三 pipeline 合并为单 daemon  
- wenjin / 下游语料仓逻辑  
- 重写 `scripts/research/`  
- OCR / 性能大改  
- 强制迁移用户 KB 目录 `ninjasin/` → `chat-watch/`（仅停止写入旧路径）

---

## 8. 阶段检查表（复制到 PR / commit）

```
## R?
- [ ] REFACTOR_INVENTORY 对应行已更新
- [ ] scripts/verify.ps1 全绿（T2/T3 手测若动 pipeline）
- [ ] pytest 无回归
- [ ] 自启/status（若动 launchers/bootstrap）
- [ ] DEV_PLAN / ARCHITECTURE 同步
- [ ] commit: Refactor R?: <one line why>
```

---

## 9. 建议执行顺序

```
R6 命名（立刻消除 ninjasin 困惑）
  ↓
R7 core（解除 _legacy 补丁）
  ↓
R8 pipelines/export（根目录减半）
  ↓
R9 mp_capture（可选，架构纯粹）
  ↓
R10 删 shim + 0 py 根目录 + 0.2.0
```

**Shadow 拍板点**：

1. R9 选方案 A 还是 B？  
2. R10 是否与 `0.2.0` 公开发 release 绑定？  
3. `stop_mp_idb_watch.bat` 等别名是否直接删（建议删，文档写 `stop_wxlocal.bat`）？
