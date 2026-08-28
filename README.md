<div align="center">

# wxlocal

> **本地读微信，不必碰云端** · *Read WeChat PC locally*
> Windows 开源工具：解密本地库 · 滑订阅号 IndexedDB · 单联系人自动导出。

[![MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Platform-Windows-0078D4)](docs/STANDALONE.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB)](pyproject.toml)
[![Disclaimer](https://img.shields.io/badge/Disclaimer-required-orange)](docs/DISCLAIMER.md)

**[github.com/NinjaSln-labs/wxlocal](https://github.com/NinjaSln-labs/wxlocal)**

</div>

---

## 简介

**wxlocal** — 读取微信 **PC 4.x** 本机 `xwechat_files`：解密聊天库、监听订阅号 IndexedDB、按联系人导出转发语料。数据默认留在本机与外置知识库目录。

- **一句话目标**：登录微信后，后台静默跑两条管道——**滑订阅号** → URL 注册表 + 开发向过滤；**转发联系人** → 导出 JSON + 增量归档。
- **边界**：自学习 / 研究工具，[免责声明必读](docs/DISCLAIMER.md)；**不是**腾讯官方 SDK，不承诺微信版本永久兼容。
- **平台**：仅 **Windows**（内存密钥提取、Chromium IndexedDB 路径均依赖 PC 客户端）。

## 当前状态

| 域 | 状态 |
|----|------|
| Core 解密 + 导出 | ✅ `run_extract.bat` · `wxlocal-export` · Web UI |
| mp-scroll（IndexedDB） | ✅ `run_mp_scroll.bat` · `wxlocal-mp-scroll` · 登录自启 |
| chat-watch（单联系人） | ✅ `run_chat_watch.bat` · `wxlocal-watch` · delta 归档 |
| mp-capture（可选） | ✅ mitmproxy addon |
| 解密缓存路径 | ✅ 统一 `output/decrypted/` |
| CI | ✅ compileall + pytest smoke |
| 验证 | ✅ `scripts/verify.ps1` |

**维护笔记：** [docs/STANDALONE.md](docs/STANDALONE.md) · **架构：** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 目录结构

| 路径 | 内容 |
|------|------|
| `wxlocal/` | 可安装包：`config` · `core` · `pipelines` · `ops` · `shared` · `web` · `export` |
| `scripts/` | verify · daemon_status · ops · research |
| `launchers/win/` | 统一 VBS 启动器（`pythonw -m …`） |
| `vendor/wcdb-key-tool-main/` | SQLCipher 解密（MIT） |
| `docs/` | DISCLAIMER · 运维 · 架构 |
| `output/` | 运行时（密钥缓存、日志、`decrypted/`，gitignore） |

## 快速开始

```powershell
git clone https://github.com/NinjaSln-labs/wxlocal.git
cd wxlocal

python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"

copy .env.example .env
# 必填：WECHAT_DATA_ROOT=D:\app\WeixinData\xwechat_files

.\run_extract.bat
```

**Daemon（推荐）：**

```powershell
.\run_chat_watch.bat          # 或 wxlocal-watch
.\run_mp_scroll.bat           # 或 wxlocal-mp-scroll
.\status_wxlocal.bat
.\stop_wxlocal.bat
```

**登录自启（无弹窗）：**

```powershell
.\setup_wxlocal_autostart.bat
.\status_wxlocal.bat
```

| 模块 | 入口 | 说明 |
|------|------|------|
| Core | `run_extract.bat` | 管理员提权 → 提取密钥 → 解密 → 导出 |
| mp-scroll | `wxlocal-mp-scroll --once` | 单次扫描 IndexedDB |
| chat-watch | `wxlocal-watch --once` | 单次同步指定联系人 |
| Web UI | `run_web.bat` / `wxlocal-web` | http://127.0.0.1:8787 |

## 配置

| 变量 | 含义 |
|------|------|
| `WECHAT_DATA_ROOT` | `xwechat_files` 根目录（**必填**） |
| `WECHAT_KB_ROOT` | 语料导出根（默认 `./data/knowledge-base`） |
| `WECHAT_WATCH_CONTACT` | chat-watch 联系人昵称（默认 `FileTransfer`） |
| `WXLOCAL_PYTHON` | 自启用 `pythonw` 路径 |
| `WECHAT_FETCH_PROXY` | 正文抓取 HTTP 代理（可选） |

分类 / 过滤规则可放在消费者 KB 的 `config/*.json`，见 [docs/STANDALONE.md](docs/STANDALONE.md)。

## 文档

| 文档 | 说明 |
|------|------|
| [DISCLAIMER](docs/DISCLAIMER.md) | **必读** — 自学习声明与合规提示 |
| [STANDALONE](docs/STANDALONE.md) | OSS 布局 · 自启 · KB 契约 |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 模块依赖与运行时结构 |
| [MP_CAPTURE](docs/MP_CAPTURE.md) | mitm / IndexedDB 细节 |
| [WECHAT_4.1.13_RESEARCH](docs/WECHAT_4.1.13_RESEARCH.md) | 4.x 解密调研笔记 |
| [LOCAL_SETUP.example](docs/LOCAL_SETUP.example.md) | 维护者本地配置模板 |

## 边界（刻意不做）

不做：云端同步、多账号 SaaS、绕过微信 ToS 的「破解」宣传、保证正文 100% 抓取。  
只做：读本机已落盘数据 + 可选代理补正文 + 可配置外置语料目录。

## Git

- 分支 `main`；PR 须在 Windows 下通过 `scripts/verify.ps1 -SkipIntegration`（或 CI）。
- 密钥、`output/`、`.env` **永不提交**。

## License

[MIT](LICENSE) · bundled [wcdb-key-tool](vendor/wcdb-key-tool-main/) (MIT)
