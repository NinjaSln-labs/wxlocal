# wxlocal · 工程交接

## 1. 交接元信息

| 项 | 内容 |
|----|------|
| 日期 | 2026-08-29 |
| 交接方 | Cursor session（Shadow / NinjaSln） |
| 接收方 | 下一 agent / session |
| 原因 | Phase R0–R10 + C3 收口；自启弹窗已修；工作区干净 |
| 一句话 | Windows 微信 PC 本地采集：解密 / mp-scroll(IDB) / chat-watch；包名 `wxlocal`，**v0.2.0** |

**文档入口（权威，勿复制）：** [README.md](README.md) · [docs/STANDALONE.md](docs/STANDALONE.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/DEV_PLAN.md](docs/DEV_PLAN.md) · [docs/REFACTOR_PLAN.md](docs/REFACTOR_PLAN.md) · [CHANGELOG.md](CHANGELOG.md)

**接收方建议动作：**
1. `git status` / `git log -5` 确认 `main` == `origin/main`
2. 读本文件 §2–§4，细节用 `git show <hash>` / 上表文档
3. 凭据与路径：只向用户确认本机 `.env` 是否仍有效（**勿提交**）；模板见 `.env.example`
4. 恢复上下文技能：`project-intake`；维护本文件用 `project-handoff`

---

## 2. 当前状态快照

| 域 | 状态 |
|----|------|
| 结构重构 R0–R10 | ✅ 根目录 `.py`=0；实现在 `wxlocal/` |
| Phase C3 legacy 目录 | ✅ `E:\workspace\wechat-reader` 已删 |
| 登录自启 | ✅ Startup 仅 `WxLocalAutostart.vbs`；根路径在 `%LOCALAPPDATA%\wxlocal\install_root.txt` |
| CI | ✅ pytest 已适配空 `WECHAT_DATA_ROOT` |
| 根 launcher | ✅ bat/vbs **10**；冗余 `run.bat` 等已删 |

**版本控制：** git · branch `main` · 与 `origin/main` 同步 · **无未提交变更** · HEAD `b988d68`

**构建环境：** `.venv` 本地已有；`pip install -e ".[dev]"`；console：`wxlocal-watch` / `wxlocal-mp-scroll` / `wxlocal-export` / `wxlocal-web`

**最近完成（一行；详情=commit message）：**
- [b988d68] Fix login popup: keep install root out of Startup folder
- [3ab8867] Trim redundant root launchers
- [206f63b] Fix CI smoke test empty DATA_ROOT
- [4b56bf3] Fix mp-scroll radium path + same-day archive overwrite
- [89da395] Release v0.2.0 remove root Python shims (R10)
- [ae3043f] R9 mp_capture → `wxlocal.pipelines.mp_scroll.capture`
- [1a5d3be] R8 export/archive/ops 迁包
- [24e8046] C3 legacy wechat-reader folder removed

**占位 / 未做边界：** 无未合并功能分支。OCR 默认关（`.env` `MP_SCROLL_OCR=0`）。mitm 抓包为可选，非默认自启。

---

## 3. 下一步与验证点

**可立即做（按需，无强制 ticket）：**
- [ ] 重启后确认 Startup **无** `*.path`，仅 VBS；自启日志见 `output/autostart_launch.log`
- [ ] 需要更多推荐流标题时：评估 `MP_SCROLL_OCR=1` + `pip install -e ".[ocr]"`（见 [docs/MP_CAPTURE.md](docs/MP_CAPTURE.md)）
- [ ] `body enrich failed` / 代理：确认本机 `WECHAT_FETCH_PROXY`（常 `127.0.0.1:6696`）是否在跑

**外部依赖来源：**
- `WECHAT_DATA_ROOT` / `WECHAT_KB_ROOT` / 联系人名 → 用户本机 `.env`（模板 `.env.example`）
- 微信进程 + 管理员密钥提取 → 用户本机微信登录态

**随后路线：** 产品向增强（OCR/正文成功率）或文档整理；结构债 R0–R10 已结。

**风险：** 改 `WxLocalAutostart.vbs` 后须重跑 `.\setup_wxlocal_autostart.bat`（Startup 是拷贝不是软链）。

---

## 4. 即时操作

```powershell
# 验证
.\scripts\verify.ps1
# 或
.\.venv\Scripts\python.exe -m pytest tests/ -q
.\status_wxlocal.bat

# 自启重装（改 VBS 后必跑）
.\setup_wxlocal_autostart.bat

# 管线
.\run_chat_watch.bat
.\run_mp_scroll.bat
.\run_extract.bat
```

**仍会踩（未当 bug 关单）：**
- mp-scroll：微信 IDB 是滑动窗口，猛滑列表 `live` 可能几乎不变、`new` 很少；OCR 关时更明显
- 正文 enrich 依赖代理可达；代理挂了会 `failed=15` / `enrich skipped`

**已修坑归档：** [HANDOFF-ARCHIVE/pits.md](HANDOFF-ARCHIVE/pits.md)

---

## 5. 引用索引

| 主题 | 权威路径 |
|------|----------|
| 产品/免责 | docs/DISCLAIMER.md · README.md |
| 运维/自启 | docs/STANDALONE.md · docs/LOCAL_SETUP.example.md |
| 架构 | docs/ARCHITECTURE.md |
| 重构计划/清单 | docs/REFACTOR_PLAN.md · docs/REFACTOR_INVENTORY.md |
| 里程碑/门禁 | docs/DEV_PLAN.md |
| mp-scroll / capture | docs/MP_CAPTURE.md |
| 版本变更 | CHANGELOG.md |
| 包入口 | pyproject.toml `[project.scripts]` |
| 本机密钥/路径 | `.env`（gitignore）· `.env.example` |

---

## 6. 维护规则

- **更新时机：** 阶段收口、跨 session 交接、修了自启/门禁类坑之后
- **防双源：** 文档与 commit 已有内容只引用 hash/路径；本文件只记 delta
- **最近完成：** 一行 `- [hash] 标题`；细节在 `git log`
- **确认已修的坑/待办：** 迁 `HANDOFF-ARCHIVE/pits.md` 或 `done.md`，勿堆在正文
- **脱敏：** 不写 `.env` 真值、密钥、个人信息
- **决策日志：** 本仓暂无 `docs/decisions/`；新阶段裁定若产生 ADR 只引用编号
