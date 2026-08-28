# wxlocal 重构计划

> **范围**：仅 `wxlocal` 本仓。不处理 wenjin / 其它仓库。  
> **原则**：小步交付、每步 `scripts/verify.ps1` 全绿、旧入口保留兼容层直至下一 major。  
> **现状**：审计（Phase A–D）已收；代码仍 **扁平散落**（根目录 ~40 个 `.py`、三套命名、库层反向依赖根脚本）。

---

## 1. 问题诊断

### 1.1 根目录过载

| 类别 | 数量 | 示例 |
|------|------|------|
| 生产 daemon / pipeline | ~12 | `watchdog.py`, `watch_mp_idb.py`, `archive_ninjasin_delta.py` |
| 生产 export | 6 | `export_contact.py`, `export_mp_dev.py`, … |
| 核心基础设施 | ~10 | `paths.py`, `config.py`, `wcdb_bridge.py`, `daemon_util.py` |
| 调试 / 一次性脚本 | ~20 | `debug_scan*.py`, `test_keys.py`, `scan_keys.py` |
| 启动器 bat/vbs/ps1 | ~33 | 多套重复 wrapper |

**症状**：新人无法从目录树判断「哪些是产品、哪些是垃圾、哪些是研究」。

### 1.2 三套命名并存

| 时代 | 仍存在的标识 |
|------|----------------|
| wechat-reader | `WeChatReaderAutostart.vbs`, `status_wechat_reader.bat`, `WECHAT_READER_PYTHON` |
| ninjasin | `bootstrap_ninjasin_watch.py`, `ninjasin_dedup.py`, `NINJASIN_STATE_DIR`, `run_ninjasin_watchdog.*` |
| wxlocal / 产品名 | `WxLocalAutostart.vbs`, `CHAT_WATCH_KB`, `WECHAT_WATCH_CONTACT` |

README 对外说 **chat-watch** + **mp-scroll**，代码和启动器仍大量 **ninjasin**。

### 1.3 依赖方向错误（最该优先修）

```
mp_capture/idb_registry.py  ──import──►  export_mp_dev.py      (根目录)
                          ──import──►  ninjasin_dedup.py      (根目录)
                          ──import──►  mp_dev_filter.py       (根目录)
```

**库包不应 import 根脚本**。这导致无法安全打包、测试边界模糊。

### 1.4 启动器重复

- `bootstrap_mp_watch.py` ≈ `bootstrap_ninjasin_watch.py`（仅目标模块不同）
- `run_mp_idb_watch.vbs` ≈ `run_ninjasin_watchdog.vbs` ≈ `WxLocalAutostart.vbs` 内嵌逻辑
- `launch_*` / `run_*` / `stop_wechat_reader` 等多为 **薄转发**，增加认知成本

### 1.5 路径与状态分散

- PID 文件：`ninjasin_watch.pid` vs `mp_idb_watch.pid`（命名不一致）
- 日志：repo `output/` + KB `state/` 双写
- 个别 stop bat 仍硬编码 `F:\ext\...`（与 `paths.py` 契约脱节）

---

## 2. 目标架构

### 2.1 逻辑分层（不急于物理搬家）

```
┌─────────────────────────────────────────────────────────┐
│  launchers/          bat · vbs · ps1（薄入口）           │
├─────────────────────────────────────────────────────────┤
│  wxlocal/            可安装 Python 包                    │
│    config/           env + paths                         │
│    core/             解密 · 读库 · wcdb                  │
│    shared/           dedup · filter · http · daemon_util │
│    pipelines/                                            │
│      chat_watch/     daemon · export · archive           │
│      mp_scroll/      daemon · idb · registry · ocr       │
│      mp_capture/     mitm addon · storage                │
│    export/           CLI 导出（messages / mp_*）          │
│    web/              Flask app + service                 │
├─────────────────────────────────────────────────────────┤
│  scripts/                                                │
│    ops/              verify · daemon_status · env helpers  │
│    research/         51 个 probe（保持不动）              │
│    legacy/           根目录迁出的 debug / 旧 scanner       │
├─────────────────────────────────────────────────────────┤
│  vendor/             wcdb-key-tool                       │
│  tests/              pytest smoke + 后续 pipeline 单测     │
└─────────────────────────────────────────────────────────┘
```

### 2.2 命名收敛（对外 vs 对内）

| 概念 | 对外名（文档/README） | 代码包名 | 兼容别名（保留 1 个 release） |
|------|----------------------|----------|------------------------------|
| 联系人同步 | chat-watch | `pipelines.chat_watch` | `ninjasin_*` 常量 re-export |
| 订阅号滑屏 | mp-scroll | `pipelines.mp_scroll` | `mp_idb_*` 日志文件名可暂留 |
| 本工具 | wxlocal | 包名 `wxlocal` | — |

### 2.3 依赖规则（重构后强制）

1. `wxlocal.config` → 无业务依赖  
2. `wxlocal.core` → 仅 config  
3. `wxlocal.shared` → config  
4. `wxlocal.pipelines.*` → core + shared + config  
5. `wxlocal.export` → core + shared  
6. **禁止** `mp_capture` / `pipelines` import 根目录模块  
7. `scripts/research` 可 import `wxlocal`，但 `wxlocal` 不得 import research  

---

## 3. 分阶段实施（R0–R5）

每阶段：**计划 → 实现 → `verify.ps1` → commit**。  
预估总工期：**2–3 周**（按每阶段 1–3 天、含手测）。

---

### R0 — 冻结与清单（0.5 天）✅ 本文档

| 交付 | 说明 |
|------|------|
| `docs/REFACTOR_PLAN.md` | 本文件 |
| `docs/REFACTOR_INVENTORY.md` | 根目录每个 `.py` 归类表（见 §4） |
| DEV_PLAN 增加 Phase R 指针 | 链到本计划 |

**验收**：团队对目标目录树与阶段顺序达成一致。

---

### R1 — 清扫根目录垃圾（低风险，1 天）✅

21 个调试/本地脚本已移至 `scripts/legacy/`；根目录 `.py` 约 40 → 25。

---

### R2 — 抽出 shared 层，打断反向依赖（核心，2–3 天）✅

`wxlocal/shared/{dedup,mp_filter,http_fetch,daemon}.py` 已落地；根目录 shim 保留；`tests/test_shared_imports.py` 锁定 import 方向。

---

### R3 — 统一启动器（1–2 天）✅

- `launchers/win/run_daemon.vbs` — 参数化 bootstrap 启动（ResolveProjectRoot / pythonw / log）
- 规范入口：`run_chat_watch.bat`、`run_mp_scroll.bat`；旧名保留转发
- `scripts/daemon_status.py stop` — 统一 stop，无 `F:\` 硬编码
- `tests/test_launchers.py` — 入口存在性 + stop bat 契约

---

### R4 — 包化入口（2–3 天）✅

- `wxlocal/config/` — `env_loader`, `paths`, `config`（根目录 shim 保留）
- `wxlocal/pipelines/chat_watch/daemon.py`、`mp_scroll/daemon.py` — daemon 实现
- `wxlocal/web/`、`wxlocal/export/cli.py` — Web 与导出 CLI
- **console_scripts**：`wxlocal-watch`, `wxlocal-mp-scroll`, `wxlocal-export`, `wxlocal-web`
- `tests/test_console_scripts.py` — import 契约

---

### R5 — 收尾与契约固化（1 天）✅

- `wxlocal/config/paths/` 按 pipeline 拆分；根 `paths.py` shim 保留
- PID/日志统一：`chat_watch.pid`、`mp_scroll.pid`；启动时迁移旧 pid 文件
- 删除 R3 遗留转发 bat（保留 `WeChatReaderAutostart.vbs` → `WxLocalAutostart.vbs`）
- `docs/ARCHITECTURE.md` 依赖图；`tests/test_pid_files.py`

**Phase R 完成。**

---

## 4. 根目录文件归类表（R1 输入）

### 保留为入口（R4 前不动）

`watchdog.py`, `watch_mp_idb.py`, `main.py`, `app.py`, `bootstrap_*.py`, `export_*.py`, `mp_registry.py`, `run_mp_capture.py`, `paths.py`, `config.py`, `env_loader.py`, `daemon_util.py`, `wcdb_bridge.py`, `scan_keys_v41.py`, `decrypt_db.py`, `read_messages.py`, `key_parser.py`, `service.py`, `subprocess_win.py`, `archive_ninjasin_delta.py`, `ninjasin_dedup.py`, `mp_dev_filter.py`, `enrich_bodies_batch.py`, `rescan_titles.py`, `reset_mp_scroll.py`, `restore_idb_backup.py`, `mp_capture_status.py`

### R1 迁至 `scripts/legacy/`

`debug_*.py`, `scan_keys.py`, `test_*.py`, `login_scan.py`, `fast_login_scan.py`, `check_dbs.py`, `extract_key_from_info.py`, `read_key_info.py`, `fetch_full_content.py`, `find_contact.py`, `parse_merged.py`, `_check_delta_bodies.py`, `_print_delta.py`, `_sample_ocr.py`

### 已在正确位置

`mp_capture/*`, `scripts/research/*`, `scripts/ops/*`, `tests/*`, `vendor/*`

---

## 5. 风险与回滚

| 风险 | 缓解 |
|------|------|
| 自启 VBS 路径变更导致登录不启动 | R3 前不改 `WxLocalAutostart.vbs` 文件名；只抽内部函数 |
| 外部脚本 import 根模块 | 全程保留 shim；grep 本仓 + README 声明 deprecate 时间表 |
| `mp_capture` 与 `wxlocal.pipelines.mp_scroll` 双份 | R4 先 **复制** 后 **删旧**；registry 只保留一份 |
| 重构期间功能回归 | 每阶段必须 T2/T3；R4 后加 `wxlocal-watch --once` 对照测试 |

**回滚策略**：每阶段独立 commit；失败则 `git revert` 单 commit，不跨阶段大块 revert。

---

## 6. 刻意不做（本计划范围外）

- 不改微信解密算法 / wcdb vendor 内部
- 不合并三条 pipeline 为单一 daemon
- 不处理 wenjin 语料仓逻辑
- 不重写 `scripts/research/` 51 个 probe
- 不做大规模性能优化或 OCR 架构变更
- 不在 R4 前改 KB 目录布局（`WECHAT_KB_ROOT` 契约不变）

---

## 7. 建议执行顺序（给 Shadow）

```
R0 读计划拍板
  ↓
R1 扫垃圾（立刻减负，零行为变化）
  ↓
R2 shared 层（解耦，收益最大）
  ↓
R3 启动器（运维体验）
  ↓
R4 包化（长期可维护）
  ↓
R5 收尾命名 + 删 shim
```

**若时间紧**：至少做 **R1 + R2**（3–4 天），已能解决「散」和「反向依赖」两大痛点。

---

## 8. 阶段完成检查表

```
## R?
- [ ] 计划章节已读，范围无蔓延
- [ ] scripts/verify.ps1（含 T2/T3 手测）
- [ ] pytest 无回归
- [ ] 自启/status 手测（若动 launchers）
- [ ] DEV_PLAN / REFACTOR_PLAN 状态更新
- [ ] commit message 标明 R? 阶段
```
