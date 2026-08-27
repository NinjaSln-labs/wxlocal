# 微信 PC 订阅号 · 网络抓包采集

> **自学习 / 研究用途。** 抓包可能违反微信用户协议，请自行评估合规风险。见 [DISCLAIMER.md](DISCLAIMER.md)。

> 解决「推荐流文章不落 `biz_message_0.db`」的问题。  
> 通过 mitmproxy 拦截 Weixin.exe 的 HTTPS 流量，提取文章标题/链接/摘要。

## 为什么需要这个

| 来源 | 能否读到推荐流 |
|------|----------------|
| `biz_message_0.db` + `export_mp_dev.py` | ❌ 仅已关注号推送 |
| **mitm 抓包** `mp_capture` | ✅ 浏览/点开即可捕获 |

## 一次性准备

### 1. 安装依赖

```powershell
cd wxlocal
.venv\Scripts\pip.exe install mitmproxy
```

### 2. 安装 mitm 证书（首次）

```powershell
.venv\Scripts\python.exe run_mp_capture.py
```

另开浏览器访问 http://mitm.it → 下载并安装 **Windows** 证书到「受信任的根证书颁发机构」。

> 微信 PC 若提示证书错误，需确认 Weixin 进程信任系统证书库。

### 3. 让微信走抓包代理

默认监听 **`127.0.0.1:8848`**，上游转发到你现有代理 **`127.0.0.1:6696`**。

**推荐：Proxifier**（WeChat 通常不读系统代理）

| 设置 | 值 |
|------|-----|
| 代理 | `127.0.0.1:8848` HTTP |
| 规则 | `Weixin.exe` → 上述代理 |
| 其他程序 | Direct（避免全局干扰） |

也可试 Windows 系统代理 → `127.0.0.1:8848`（部分版本无效）。

环境变量：

```powershell
$env:MP_CAPTURE_PORT="8848"
$env:MP_CAPTURE_UPSTREAM="http://127.0.0.1:6696"   # 留空=直连
$env:MP_CAPTURE_RAW="1"      # 保存原始响应到 raw/
```

## 只滑列表（推荐，无需 mitm）

订阅号列表由 **WeChatAppEx** 渲染，文章 URL 缓存在 IndexedDB，**不必开抓包代理**。

IndexedDB 有 LRU 上限，旧 URL 会被挤掉 → 用 **后台 pipeline** 累积 + 自动 enrich：

```powershell
# 后台（15s 一轮：扫 IDB → 抓标题/正文 → 开发向导出）
.\run_mp_idb_watch.bat
.\stop_mp_idb_watch.bat
.\status_mp_idb_watch.bat          # 进程 + 最近日志/错误

# 登录后自动启动（一次性，无需管理员）
.\setup_mp_idb_autostart.ps1
# 卸载: .\setup_mp_idb_autostart.ps1 -Uninstall
# 状态: .\status_wechat_reader.bat

# 手动跑一轮
.venv\Scripts\python.exe watch_mp_idb.py --once

# 查看
.venv\Scripts\python.exe mp_registry.py list
```

**前提：** 微信走代理 **6696**（`WECHAT_FETCH_PROXY`），否则只累积 URL、不抓标题。

注册表：`F:\ext\knowledge-base\wechat\mp-capture\registry\idb_registry.json`  
开发向语料：`F:\ext\knowledge-base\wechat\mp-scroll\exports\mp_scroll_dev_latest.json`

一次性快照（不过滤、不累积）：

```powershell
.venv\Scripts\python.exe export_mp_idb.py              # 仅导出 URL
.venv\Scripts\python.exe export_mp_idb.py --fetch-titles   # 抓标题+开发向过滤
```

输出：`F:\ext\knowledge-base\wechat\mp-capture\exports\mp_idb_latest.json`

> 使用此方式时：**可关闭** `run_mp_capture` / Proxifier 的 8848 规则。  
> `fetch-title` / `fetch-body` 需要微信代理 **6696**（`WECHAT_FETCH_PROXY`）。

## mitm 抓包（可选，点开文章时补充）

```powershell
# 后台启动（最小化窗口，日志 output/mp_capture.log）
.\run_mp_capture.bat
.\stop_mp_capture.bat   # 停止

# 或前台调试
.venv\Scripts\python.exe run_mp_capture.py
```

## 输出位置

```
F:\ext\knowledge-base\wechat\mp-capture\
├── registry\idb_registry.json       # 持久 URL 注册表（监控累积）
├── exports\idb_registry_latest.json # 注册表快照
├── exports\mp_idb_latest.json         # 一次性 IDB 导出
├── exports\mp_capture_latest.json   # mitm 最新快照
├── archive\YYYY-MM-DD-capture\      # 按日批次
├── raw\                             # 原始 HTTP 响应（调试用）
└── INDEX.md
```

## 故障排查

| 现象 | 处理 |
|------|------|
| 终端无 `[mp-capture]` 输出 | Weixin 未走 8848；检查 Proxifier 规则 |
| 有流量但无文章 | 看 `raw/` 里响应格式，反馈路径以便加解析器 |
| 证书错误 / 无法打开文章 | 重装 mitm 根证书；或微信证书钉扎需额外绕过 |
| 只有部分域名 | 正常；点开文章时会请求 `mp.weixin.qq.com/s?...` |

## 与 mp-dev 的关系

| 管道 | 数据源 | 适用 |
|------|--------|------|
| `export_mp_dev.py` | 本地 DB | 已关注号历史推送 |
| `export_mp_capture.py` | mitm 抓包 | **推荐流 / 未关注** |

两者语料目录并列：`mp-dev/` vs `mp-capture/`。
