# WeChat PC 4.1.13.12 (Windows) 数据库解密研究

> 研究日期：2026-08-25  
> 目标环境：WeChat `D:\app\Weixin\Weixin.exe` v4.1.13.12，数据目录 `D:\app\WeixinData\xwechat_files\sndddepdc_who_29ad\`  
> 用途：长期参考文档，供 `wxlocal` 项目及后续版本升级时查阅

---

## 目录

1. [版本演进：4.0.x → 4.1.x 关键变化](#1-版本演进40x--41x-关键变化)
2. [密钥提取方法全景](#2-密钥提取方法全景)
3. [开源工具状态评估（4.1.13）](#3-开源工具状态评估4113)
4. [数据库结构（4.1.x）](#4-数据库结构41x)
5. [推荐工作流（Windows 4.1.13.12）](#5-推荐工作流windows-411312)
6. [后台守护进程（可选）](#6-后台守护进程可选)
7. [局限性与风险](#7-局限性与风险)
8. [未来版本监控清单](#8-未来版本监控清单)
9. [参考资料](#9-参考资料)

---

## 1. 版本演进：4.0.x → 4.1.x 关键变化

### 1.1 加密算法（未变）

微信 4.x 全线使用 **SQLCipher 4**（经 WCDB 封装），核心参数自 4.0 起稳定：

| 参数 | 值 |
|------|-----|
| 对称加密 | AES-256-CBC |
| 消息认证 | HMAC-SHA512 |
| 密钥派生 (KDF) | PBKDF2-HMAC-SHA512 |
| KDF 迭代次数 | 256,000 |
| 页大小 (page_size) | 4096 字节 |
| 保留区 (reserve) | 80 字节（IV 16 + HMAC 64） |
| IV 偏移 | 4016（每页末尾倒数第 80~64 字节） |
| HMAC 偏移 | 4032（每页末尾 64 字节） |

**每页布局：**

```
[0:16]     = salt（仅第 1 页；后续页复用第 1 页 salt）
[16:4016]  = 加密数据（第 1 页含 SQLite 头被加密部分）
[4016:4032] = IV
[4032:4096] = HMAC-SHA512
```

**HMAC 验证公式（SQLCipher 4 标准）：**

```python
mac_salt = db_salt XOR 0x3a
mac_key  = PBKDF2-HMAC-SHA512(enc_key, mac_salt, iterations=2, dklen=32)
valid    = HMAC-SHA512(mac_key, page1[16:4032] + pack('<I', 1)) == page1[4032:4096]
```

**每个 `.db` 文件有独立 salt（文件头 16 字节），但共享同一个 account-level passphrase。**

```python
enc_key = PBKDF2-HMAC-SHA512(passphrase, db_salt, iterations=256000, dklen=32)
```

### 1.2 密钥缓存机制的三次变迁

| 阶段 | 版本范围 | 内存中的形态 | 被动扫描 |
|------|----------|-------------|----------|
| **A：raw key 缓存** | 4.0.x ~ 4.1.9.x（Windows） | `x'<64hex_enc_key><32hex_salt>'` 字符串 | ✅ 有效 |
| **B：passphrase 半驻留** | 4.1.1+（Linux/macOS 更早） | 32 字节 passphrase 二进制，Config.Cipher 对象可扫描 | ⚠️ 需 PBKDF2 派生 |
| **C：零驻留** | **4.1.10+**（Windows，2025-05 起） | enc_key 派生后即用即弃，稳态内存无任何可寻形态 | ❌ 无效 |

**关键时间节点（社区验证）：**

- **2025-05-13**：Issue #96 首次报告 Linux/macOS 4.1+ 不再缓存 raw key
- **2025-05-24**：Windows 4.1.9.57 仍可用 `x'96hex'` 扫描，27/27 命中
- **2025-05-27**：Windows 4.1.10.24 首次报告 0 候选（Issue #125）
- **2025 系统性验证**（Issue #152）：对 4.1.10.53 做 1.3GB 内存 dump + 离线穷举，确认 enc_key 以任何形态均不驻留
- **2025 下半年**：4.1.11+ 进一步移除 `x'96hex'` 模式，passphrase 仅在 codec 配置函数调用瞬间出现
- **4.1.12.26**：stargazer-2026 用 Frida spawn hook `Weixin.dll` MMV1 函数验证 25/25 解密成功
- **4.1.13.12**（当前版本）：继承 4.1.10+ 零驻留策略，被动扫描确定无效

### 1.3 重要不变量

1. **数据库加密算法和 passphrase 在版本升级时不改变**——4.1.9 提取的 key 在 4.1.13 上仍有效（27/27 HMAC 验证通过）
2. **passphrase 与账号绑定**，不随微信进程重启而变（但 lazy-loaded 的 DB 可能需要触发加载）
3. **同一账号 Windows / macOS 的 key 不通用**（平台相关派生）
4. **手机端 Backup.db 使用独立密钥**，PC 端无法解密

### 1.4 数据目录结构变化（4.0 → 4.1）

4.1 起数据目录从 `%USERPROFILE%\Documents\WeChat Files\` 迁移到自定义路径下的 `xwechat_files\`：

```
D:\app\WeixinData\xwechat_files\
├── sndddepdc_who_29ad\          # 账号数据目录（wxid_hash 格式）
│   ├── db_storage\              # ★ 加密数据库（目标目录）
│   │   ├── message\
│   │   │   ├── message_0.db     # 最新消息分片
│   │   │   ├── message_1.db
│   │   │   ├── message_fts.db   # 全文索引（通常不解密）
│   │   │   └── message_resource.db
│   │   ├── session\session.db
│   │   ├── contact\contact.db
│   │   ├── media_0.db
│   │   └── ...（约 25~30 个 .db）
│   ├── msg\                     # 媒体文件（图片/语音/视频）
│   └── config\
├── all_users\
│   └── login\
│       └── sndddepdc_who\
│           └── key_info.db      # 登录密钥元信息（见 §2.5）
└── ...
```

配置文件位置：`%APPDATA%\Tencent\xwechat\config\<hash>.ini`（含 `MyDocument:` 等路径关键字）

---

## 2. 密钥提取方法全景

### 2.1 方法一：被动内存扫描 `x'96hex'` 模式

**原理：** 扫描 `Weixin.exe` 进程内存，匹配 `x'<64hex_enc_key><32hex_salt>'` 正则，用 HMAC 校验 page 1。

**状态：❌ 4.1.13.12 无效**

4.1.10 起 Windows 已彻底移除该缓存。社区对 4.1.10.53 做了完整验证：
- `x'96hex'` 模式：0 个
- raw key 32 字节直接搜索：0 次
- XOR/翻转/拆半等变换：全无
- salt 邻域指针解引用：无

**适用工具（均失效于 4.1.10+）：** wechat-decrypt、chatlog（内置扫描）、wx-cli、L1en2407/wechat-decrypt

### 2.2 方法二：Config.Cipher 运行时对象扫描 + PBKDF2

**原理：** 在进程内存中定位 `com.Tencent.WCDB.Config.Cipher` 字符串附近的 WCDB 配置对象，解码候选 passphrase，再用 PBKDF2 派生 enc_key 并 HMAC 验证。

**状态：⚠️ 4.1.10+ 大概率无效，4.1.1~4.1.9 可能有效**

wcdb-key-tool 在 Windows 4.1+ 上声称此为主路径，但：
- 4.1.10.27 实测 0 候选（Issue #89）
- 4.1.10.53 系统性验证确认零驻留
- `wxlocal` 项目的 `scan_keys_v41.py` 已实现此逻辑，在 4.1.13.12 上未成功

**操作步骤（wcdb-key-tool）：**

```powershell
# 以管理员运行
git clone https://github.com/TANGandXUE/wcdb-key-tool.git
cd wcdb-key-tool
pip install pycryptodome
python wcdb_key_tool_windows.py extract --db-dir "D:\app\WeixinData\xwechat_files\sndddepdc_who_29ad\db_storage"
```

成功时 passphrase 缓存到 `~/.wcdb-key-tool/wechat-passphrase.json`（权限 600）。

### 2.3 方法三：调试器断点（x64dbg / WinDbg）

**原理：** 在 `Weixin.dll` 中定位 WCDB `setCipherKey` / codec 配置函数，在数据库打开时断点捕获 passphrase。

**定位方法：**

1. IDA/Ghidra 加载 `D:\app\Weixin\Weixin.dll`
2. 搜索字符串 `com.Tencent.WCDB.Config.Cipher` 或 `MMV1`
3. 追踪交叉引用找到处理函数
4. 计算 RVA，断点地址 = `Weixin.dll 基址 + RVA`

**已知偏移（版本相关，不可直接复用）：**

| 版本 | 定位线索 | RVA / 偏移 |
|------|----------|-----------|
| 4.1.1.19 | `com.Tencent.WCDB.Config.Cipher` xref | `0x4AEA40` |
| 4.1.12.26 | `MMV1` 字符串 xref | `0x3486140` |
| 4.1.13.12 | **需自行逆向** | 未知 |

**x64dbg 操作流程：**

```
1. 完全退出微信
2. 启动 x64dbg → File → Open → Weixin.exe（或 Attach 后重新登录）
3. 在 Weixin.dll+RVA 设软件断点
4. 运行，扫码/密码登录
5. 断点命中时：
   - 4.1.1.x：查看 RDX 寄存器 → [RDX+8] 指向 32 字节 passphrase
   - 4.1.12.x：查看 RCX 寄存器 → 结构体前 32 字节 = passphrase
6. 记录 64 位 hex，立即保存到安全位置
```

**注意：** 每次微信小版本更新，RVA 几乎必定变化。

### 2.4 方法四：Frida Hook（spawn 模式）

**原理：** 用 Frida 在进程启动最早期注入，hook codec 配置函数入口，在 onEnter 中读取 RCX 指向结构的 password 字段。

**状态：✅ 4.1.12 已验证，4.1.13 理论可行（需更新偏移）**

```python
import frida, sys

WEIXIN = r"D:\app\Weixin\Weixin.exe"
# ⚠️ 偏移仅适用于 4.1.12.26，4.1.13.12 需重新定位
HOOK_OFFSET = 0x3486140

pid = frida.spawn(WEIXIN)
session = frida.attach(pid)
script = session.create_script(f"""
var base = Process.getModuleByName('Weixin.dll').base;
Interceptor.attach(base.add({HOOK_OFFSET}), {{
    onEnter: function(args) {{
        // x64 fastcall: RCX = args[0]
        var pw = Memory.readByteArray(args[0], 32);
        send({{type: 'password', data: pw}});
    }}
}});
""")
def on_message(msg, data):
    if msg['type'] == 'send':
        print('PASSPHRASE:', data.hex() if data else msg['payload'])
script.on('message', on_message)
script.load()
frida.resume(pid)
sys.stdin.read()
```

**关键限制：**
- 必须 **spawn**（启动时注入），attach 已运行进程会错过密钥设置时机
- 存在 anti-hook 检测，可能导致微信崩溃或弹错误报告
- 有封号风险（见 §6）

### 2.5 方法五：key_info.db

**路径：** `xwechat_files\all_users\login\<account>\key_info.db`

**表结构：**

```sql
-- LoginKeyInfoTable
key_md5       TEXT   -- key_info_data 的 MD5
key_info_md5  TEXT
key_info_data BLOB   -- 加密的密钥元数据（数百~数千字节）
```

**状态：❌ 不能直接作为 passphrase 使用**

`key_info.db` 存储的是登录密钥的**加密包装**，不是明文 passphrase。`wxlocal` 项目已测试：
- 滑动窗口扫描 `key_info_data` 中所有 32/48 字节块
- PBKDF2 多种参数组合
- 均无法通过 HMAC 验证

该文件可能用于微信自身的登录态恢复，而非数据库解密的直接密钥源。

### 2.6 方法六：降级提取 + 升级（最安全）

**原理：** 在 VM 或备用机器安装微信 ≤4.1.9，登录同一账号，用传统内存扫描提取 passphrase/raw key，保存后升级回 4.1.13。

**状态：✅ 社区广泛验证，零注入风险**

```
1. 下载微信 4.1.9.x 安装包（官方历史版本或社区存档）
2. 安装到干净环境，登录目标账号
3. 运行 find_all_keys.py / wcdb-key-tool / wx_key 提取密钥
4. 保存 passphrase（64 hex）到安全位置
5. 升级回 4.1.13.12
6. 用保存的 passphrase + PBKDF2 正常解密
```

**版本存档：**
- https://github.com/cscnk52/wechat-windows-versions
- https://github.com/iibob/WechatWindowsVersionHistory

**注意：** 降级前备份 `xwechat_files` 目录；禁止自动更新（hosts 屏蔽 `dldir1.qq.com`）。

### 2.7 方法七：重新登录时机窗口

**原理：** passphrase 在登录/数据库初始化时短暂出现在寄存器或栈上。完全退出微信 → 重新登录 → 立即扫描/断点。

**实操建议：**

```
1. 微信设置 → 退出登录（不是关窗口，是退出账号）
2. 确认 Weixin.exe 进程全部退出（任务管理器检查）
3. 以管理员启动提取工具（断点或扫描）
4. 启动/登录微信
5. 在登录完成后的 5~30 秒内，数据库逐个打开，断点会多次命中
6. 同一个 passphrase 适用于所有 DB（只需捕获一次）
```

**wcdb-key-tool 说明：** 首次提取需要「退出登录再重新登录」以触发密钥重新计算。  
**chatlog FAQ：** 完全退出 PC 微信重新登录（PID 不同）后手动执行可正常获取。

对于 4.1.10+ 零驻留版本，「重新登录 + 被动扫描」仍然无效，必须配合断点/Hook。

### 2.8 方法八：wx_key GUI 工具（DLL 注入）

**项目：** https://github.com/ycccccccy/wx_key（活跃 fork：https://github.com/bubuqing99/wx_key）

**原理：** 通过 `wx_key.dll` 注入 `Weixin.exe`，hook 密钥设置函数，GUI 一键获取。

**状态：⚠️ 声称支持所有 4.x，实测版本至 4.1.5.11；4.1.13 需自行测试**

社区反馈（chatlog Issue #317）：Windows 4.1.x 用户用 wx_key 手动获取密钥后粘贴到 chatlog 可正常解密。注意 chatlog 需要 **hex 格式**（32 字节 = 64 hex 字符），不是 8 字符的显示格式。

**操作流程：**

```
1. 下载 wx_key Release（app.zip）
2. 解压到纯英文路径（避免中文路径导致 DLL 加载失败）
3. 先登录微信
4. 运行 wx_key.exe → 获取数据库密钥
5. 复制 64 位 hex 字符串
6. 粘贴到 wxlocal Web UI (http://127.0.0.1:8787)
```

---

## 3. 开源工具状态评估（4.1.13）

### 综合评级表

| 工具 | 4.1.13 可用性 | 方法 | 风险 | 推荐度 |
|------|--------------|------|------|--------|
| **wx_key** | ⚠️ 待验证 | DLL Hook GUI | 中（注入） | ★★★★☆ |
| **stargazer-2026/wechat-4.1.12-decrypt** | ⚠️ 需更新偏移 | Frida spawn | 中高 | ★★★★☆ |
| **TANGandXUE/wcdb-key-tool** | ❌ 4.1.10+ 大概率失败 | 内存扫描 | 低 | ★★☆☆☆ |
| **MWH-HEU/chatlog-keeper** | ⚠️ 需 active 模式 | 扫描+调试器 | 中 | ★★★☆☆ |
| **zhizunbao84/wetrace** | ⚠️ 待验证 | Hook 提取 | 中 | ★★★☆☆ |
| **jackwener/wx-cli** | ❌ 0 候选 | 内存扫描 | 低 | ★☆☆☆☆ |
| **sjzar/chatlog** | ❌ 内置扫描失效 | 内存扫描 | 低 | ★★☆☆☆（仅解密） |
| **L1en2407/wechat-decrypt** | ❌ 仅 raw key 扫描 | 内存扫描 | 低 | ★☆☆☆☆ |
| **ylytdeng/wechat-decrypt** | ❌ 同上 | 内存扫描 | 低 | ★☆☆☆☆ |
| **降级 4.1.9 提取** | ✅ 确定可行 | 传统扫描 | 无 | ★★★★★ |
| **wxlocal（本项目）** | ⚠️ 扫描失败 | 扫描+手动粘贴 | 低 | ★★★☆☆（解密端） |

### 3.1 L1en2407/wechat-decrypt

- **仓库：** https://github.com/L1en2407/wechat-decrypt
- **状态：** ylytdeng/wechat-decrypt 的 fork，仍基于 `x'96hex'` 内存扫描
- **4.1.13：** ❌ 不可用（无 PBKDF2 passphrase 支持）
- **价值：** 解密管线、MCP Server、monitor_web 可参考；密钥提取需换方案

### 3.2 TANGandXUE/wcdb-key-tool

- **仓库：** https://github.com/TANGandXUE/wcdb-key-tool
- **亮点：** 三平台统一工具；Linux GDB / macOS LLDB 断点方案成熟
- **Windows 4.1+：** 声称 Config.Cipher 运行时扫描有效，但 4.1.10+ 社区报告 0 命中
- **4.1.13：** 可尝试，但不抱期望；若失败需用 `capture-experimental` 断点模式

### 3.3 stargazer-2026/wechat-4.1.12-decrypt

- **仓库：** https://github.com/stargazer-2026/wechat-4.1.12-decrypt
- **验证：** 4.1.12.26 上 25/25 DB 解密成功
- **核心贡献：** 完整的 Frida hook 方案 + PBKDF2 解密脚本 + 消息解析踩坑文档
- **4.1.13：** 需用 IDA 重新定位 `MMV1` 函数偏移（4.1.12 的 `0x3486140` 不可直接用）
- **附带知识：** real_sender_id 逐库映射、WAL 解密、zstd 解压

### 3.4 jackwener/wx-cli

- **仓库：** https://github.com/jackwener/wx-cli
- **语言：** Rust CLI
- **4.1.10.27：** 0 候选（Issue #89），且存在 COM 未初始化导致路径检测失败的 bug
- **4.1.13：** ❌ 不可用

### 3.5 sjzar/chatlog

- **仓库：** https://github.com/sjzar/chatlog
- **定位：** Go 实现，带 TUI/Web UI 的聊天记录查看器
- **密钥提取：** 内置内存扫描，4.0.3.36 以上失效（FAQ Issue #197）
- **4.1.13：** 密钥提取 ❌，但可**手动输入密钥**后正常解密和浏览
- **配合 wx_key 使用：** 社区验证可行（Issue #317）

### 3.6 zhizunbao84/wetrace

- **仓库：** https://github.com/zhizunbao84/wetrace
- **定位：** Go + React 聊天记录取证/分析工具
- **方法：** Hook 运行中微信进程提取 DB Key 和图片 Key
- **4.1.13：** ⚠️ 未明确标注版本上限，需实测；仅支持 Windows

### 3.7 其他值得关注的项目

| 项目 | 说明 |
|------|------|
| [ycccccccy/wx_key](https://github.com/ycccccccy/wx_key) | Windows GUI 密钥提取，社区广泛使用 |
| [MWH-HEU/chatlog-keeper](https://github.com/MWH-HEU/chatlog-keeper) | 支持 4.1.10.31+ active 调试器提取 + QQ |
| [CN-Grace/Wechat-Emoticon-Parser](https://github.com/CN-Grace/Wechat-Emoticon-Parser) | 4.1.x 表情导出，内嵌 Config.Cipher 扫描 |
| [BoXu1225/wechat-decrypt-export](https://github.com/BoXu1225/wechat-decrypt-export) | macOS 导出工具，文档详细的 zstd/表结构说明 |
| [runzhliu/welink](https://github.com/runzhliu/welink) | 数据库 schema 文档质量高 |

---

## 4. 数据库结构（4.1.x）

### 4.1 db_storage 目录布局

```
db_storage/
├── contact/
│   ├── contact.db           # 联系人（username, nick_name, remark）
│   └── contact_fts.db       # 联系人全文索引
├── session/
│   └── session.db           # 会话列表（SessionTable）
├── message/
│   ├── message_0.db         # 最新消息分片 ★
│   ├── message_1.db         # 历史分片
│   ├── message_2.db
│   ├── biz_message_0.db     # 公众号消息
│   ├── message_fts.db       # 消息全文索引
│   ├── message_resource.db  # 媒体资源索引
│   └── media_0.db           # 媒体元数据
├── favorite/
│   ├── favorite.db
│   └── favorite_fts.db
├── emoticon/emoticon.db
├── head_image/head_image.db
├── sns/sns.db               # 朋友圈
├── hardlink/hardlink.db     # 文件硬链接索引
├── general/general.db
├── MMKV/                    # KV 存储
└── solitaire/solitaire.db
```

约 25~30 个加密 `.db` 文件，每个有独立 salt，共享同一 passphrase。

### 4.2 消息表结构

每个联系人/群聊对应一张 `Msg_<MD5(username)>` 表：

```sql
-- 示例：Msg_a1b2c3d4e5f6...（MD5 of "wxid_xxx" 或 "xxx@chatroom"）
CREATE TABLE Msg_xxx (
    local_id                  INTEGER PRIMARY KEY,
    server_id                 INTEGER,
    local_type                INTEGER,    -- 消息类型（见下表）
    sort_seq                  INTEGER,
    real_sender_id            INTEGER,    -- 关联 Name2Id.rowid
    create_time               INTEGER,    -- Unix 时间戳（秒）
    status                    INTEGER,
    upload_status             INTEGER,
    download_status           INTEGER,
    server_seq                INTEGER,
    origin_source             INTEGER,
    source                    TEXT,
    message_content           BLOB,       -- 消息内容（可能 zstd 压缩）
    compress_content          BLOB,       -- 备用压缩字段
    packed_info_data          BLOB,       -- Protobuf 附件元数据
    WCDB_CT_message_content   INTEGER,    -- 压缩类型：0=明文, 4=zstd
    WCDB_CT_source            INTEGER
);
```

**Name2Id 表（每个 message_N.db 独立）：**

```sql
CREATE TABLE Name2Id (
    user_name TEXT,
    is_group  INTEGER
);
-- rowid 对应 Msg_*.real_sender_id
```

### 4.3 消息类型（local_type）

使用 `local_type & 0xFFFF` 获取基础类型：

| local_type | 类型 | 内容格式 |
|-----------|------|----------|
| 1 | 文本 | UTF-8 明文或 zstd 压缩 |
| 3 | 图片 | XML / protobuf |
| 34 | 语音 | XML（silkv3 格式） |
| 43 | 视频 | XML |
| 47 | 表情 | XML（含 sticker 信息） |
| 49 | 富媒体 | XML（链接/文件/红包/转账/小程序） |
| 10000 | 系统消息 | 撤回通知等 |

### 4.4 ZSTD 压缩

约 30% 的消息（尤其是 type 49）使用 zstd 压缩：

```python
import zstd

if row['WCDB_CT_message_content'] == 4:
    content = zstd.decompress(row['message_content']).decode('utf-8')
else:
    content = row['message_content']  # 直接 UTF-8 文本
```

群聊文本消息格式：`wxid_xxxx:\n实际消息内容`

### 4.5 关键踩坑：real_sender_id 逐库不同

> 来源：stargazer-2026 实战经验

- `message_0.db`（最新）：`real_sender_id` = `Name2Id.rowid`（全局 wxid 映射）
- `message_1/2.db`（历史）：`real_sender_id` 可能是会话内角色编号（1/2），且不同库含义可能相反
- 必须用「锚点句」逐库校验发送者映射后再做导出

### 4.6 SQLCipher 4 解密参考实现

```python
from hashlib import pbkdf2_hmac
from Crypto.Cipher import AES

PAGE_SIZE = 4096
KDF_ITER = 256000
IV_OFFSET = 4016

def derive_enc_key(passphrase: bytes, salt: bytes) -> bytes:
    return pbkdf2_hmac("sha512", passphrase, salt, KDF_ITER, dklen=32)

def decrypt_page(enc_key: bytes, page_data: bytes, pgno: int) -> bytes:
    iv = page_data[IV_OFFSET:IV_OFFSET + 16]
    if pgno == 1:
        encrypted = page_data[16:IV_OFFSET]
        content = b"SQLite format 3\x00" + AES.new(enc_key, AES.MODE_CBC, iv).decrypt(encrypted)
    else:
        encrypted = page_data[:IV_OFFSET]
        content = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(encrypted)
    return content + b"\x00" * (PAGE_SIZE - len(content))
```

---

## 5. 推荐工作流（Windows 4.1.13.12）

> **本机实测更新（2026-08-25）：** 在 4.1.13.12 上，登录后以管理员运行 `wcdb-key-tool` 的 Config.Cipher 扫描，**20/20 数据库密钥全部提取成功**。自研 `scan_keys_v41.py` 被动扫描仍无效。建议优先使用已验证的 wcdb-key-tool 流程。

### 方案 A：wcdb-key-tool 一键提取（本机已验证 ✅）

```
难度：★☆☆  风险：低  成功率：高（登录后 + 管理员）

1. 确保微信已登录
2. 双击 run_extract.bat（自动提权）
   或手动运行 wcdb-key-tool extract → decrypt → export_messages.py
3. 查看 output\messages.json 或 Web UI http://127.0.0.1:8787
```

### 方案 B：wx_key 一键提取（备选）

```
难度：★☆☆  风险：中  成功率：中高

1. 下载 https://github.com/ycccccccy/wx_key/releases 最新版
2. 解压到纯英文路径（如 C:\tools\wx_key\）
3. 正常登录微信 4.1.13.12
4. 以管理员运行 wx_key.exe
5. 点击获取数据库密钥 → 复制 64 位 hex
6. 打开 wxlocal Web UI：http://127.0.0.1:8787
7. 粘贴 passphrase → 解密并读取
8. 将 passphrase 安全保存（密码管理器 / 加密文件）
```

### 方案 B：降级 4.1.9 提取（最安全、最可靠）

```
难度：★★☆  风险：无  成功率：确定

1. 备份 D:\app\WeixinData\xwechat_files\
2. 在 VM 或备用目录安装微信 4.1.9.x
3. 登录同一账号
4. 运行 find_all_keys.py 或 wcdb-key-tool 提取密钥
5. 保存 passphrase / all_keys.json
6. 恢复使用 4.1.13.12
7. 用 wxlocal 正常解密（passphrase 跨版本有效）
8. 屏蔽自动更新：
   # 管理员 PowerShell
   Add-Content C:\Windows\System32\drivers\etc\hosts "`n127.0.0.1 dldir1.qq.com`n127.0.0.1 dldir1v6.qq.com"
```

### 方案 C：Frida Hook（技术用户）

```
难度：★★★★  风险：中高  成功率：高（偏移正确时）

1. pip install frida frida-tools pycryptodome
2. IDA 分析 D:\app\Weixin\Weixin.dll：
   - 搜索 "MMV1" 或 "com.Tencent.WCDB.Config.Cipher"
   - 记录 codec 配置函数 RVA
3. 修改 stargazer-2026 的 Frida 脚本中的 HOOK_OFFSET
4. 完全退出微信
5. python hook_capture.py（spawn 模式）
6. 微信启动并登录 → 捕获 passphrase
7. 粘贴到 wxlocal
```

### 方案 D：x64dbg 手动断点

```
难度：★★★★★  风险：中  成功率：高

1. 下载 x64dbg
2. IDA 定位 setCipherKey / MMV1 函数 RVA
3. 退出微信 → x64dbg 打开 Weixin.exe
4. Weixin.dll 基址 + RVA 设断点
5. 运行 → 登录 → 断点命中
6. 查看 RCX（4.1.12+）或 RDX（4.1.1.x）→ 读取 32 字节 passphrase
7. 记录 hex → 粘贴到 wxlocal
```

### 方案 E：wxlocal 本项目（已有 passphrase 时）

```
难度：★☆☆  风险：无  前提：已有 64 位 hex passphrase

# Web UI（推荐）
cd E:\workspace\wxlocal
.\run_web.bat
# 浏览器 http://127.0.0.1:8787 → 粘贴 passphrase → 解密并读取

# 命令行
.\.venv\Scripts\activate
python main.py --data-root "D:\app\WeixinData\xwechat_files"
```

### 提取后的长期维护

```
1. passphrase 保存到安全位置（不会随微信升级失效）
2. 每次微信大版本升级后：
   a. 先用已有 passphrase 尝试解密 message_0.db
   b. 若 HMAC 验证失败 → 重新提取（可能换了加密方案）
3. 定期复制解密后的 DB 或导出 JSON 备份
4. 新增 message_N.db 分片时无需重新提取（同一 passphrase）
```

---

## 6. 后台守护进程（可选）

> 调研日期：2026-08-25  
> **推荐工作流：手动触发** — 登录微信后双击 `run_extract.bat`，查看 `output/messages.json` 或 Web UI。  
> 本节描述的守护进程方案为**可选高级功能，默认不用**；适合不想每次手动双击的用户。

### 6.1 结论摘要

| 问题 | 答案 |
|------|------|
| **推荐方式？** | **手动触发** — 登录微信 → `run_extract.bat` → 查看输出 |
| **4.1.13 能否全自动？** | **有条件 YES** — 需一次性配置自启守护进程；日常仅需登录微信 |
| **完全零配置？** | **NO** — 首次需管理员权限 + 任务计划注册 |
| **密钥每次都要重新提取？** | **NO** — passphrase 跨会话有效，缓存后可跳过重提取 |
| **官方 API？** | **仅企业微信**会话存档 SDK，个人微信 PC 无官方接口 |

### 6.2 各方案全自动能力评级

| 方案 | 4.1.13.12 | 登录后零操作 | 一次性配置 | 需管理员 | 可集成 wxlocal |
|------|-----------|-------------|-----------|---------|---------------------|
| **wxlocal 守护进程**（本项目） | ✅ 已验证 | ✅（配置后） | 运行 `setup_autostart.ps1` | 首次提取需；后续可仅解密 | ✅ 原生 |
| **wcdb-key-tool + 任务计划** | ✅ 20/20 | ✅（配置后） | 编写 bat + schtasks | 提取时需 | ✅ 已集成 |
| **chatlog-keeper** | ⚠️ 需 debugger | ⚠️ 被动扫描 4.1.10+ 失效 | pip install + 缓存 key | active 模式需 | 可导出后导入 |
| **wetrace** | ⚠️ 待验证 | ❌ 需点「获取密钥」 | 安装 + 路径配置 | Hook 需 | 密钥可复用 |
| **wx_key** | ⚠️ 待验证 | ❌ 需手动点 GUI | 下载解压 | 是 | 密钥粘贴到 Web UI |
| **L1en2407/monitor_web** | ❌ 内存扫描失效 | ❌ | — | 是 | 不适用 |
| **sjzar/chatlog** | ❌ 仓库已删 | ❌ | — | — | 不可用（2025-10 删库） |
| **Frida spawn hook** | ⚠️ 需更新偏移 | ⚠️ 可脚本化 | IDA 逆向 + 偏移 | 是 | 捕获后粘贴 |
| **降级 4.1.9 提取** | ✅ | ✅（密钥永久） | VM 降级流程 | 首次需 | ✅ 粘贴 passphrase |
| **企业微信会话存档** | — | ✅ 官方 | 企业资质 + SDK | 否 | 不同产品 |

### 6.3 为什么「纯登录」不够？

4.1.10+ 的「零驻留」策略意味着：

1. **稳态内存无密钥** — 微信登录完成后，passphrase 不在可被被动扫描的位置
2. **密钥只在 DB 打开瞬间出现** — wcdb-key-tool 的 Config.Cipher 扫描需在登录后、DB 被访问时运行
3. **读取进程内存需管理员** — `ReadProcessMemory` 在 Windows 上通常需要提升权限
4. **passphrase 与账号绑定且稳定** — 提取一次后缓存到 `all_keys.json`，后续解密不需要再扫内存

因此「全自动」的正确模型是：

```
一次性配置 → 登录自启守护进程（管理员）
    → 检测 Weixin.exe 启动
    → 有缓存密钥？→ 直接解密导出
    → 无缓存？→ wcdb-key-tool extract → 解密 → 导出
    → 监听 db 文件 mtime 变化 → 增量同步
```

### 6.4 各工具后台监控能力

| 工具 | 自动检测微信 | 定时同步 | 实时监听 | 说明 |
|------|------------|---------|---------|------|
| wetrace | ✅ 路径自动探测 | ✅ 5~1440 分钟 | ✅ 关键词监控 | 但密钥需手动点按钮 |
| L1en2407 monitor_web | ✅ 进程检测 | ✅ 30ms WAL 轮询 | ✅ SSE 推送 | 4.1.10+ 密钥提取失效 |
| chatlog-keeper | ✅ probe 命令 | ❌ 手动 export | ❌ | 密钥缓存后离线可用 |
| wangfan0524/wechat-msg-mcp | ⚠️ | ⚠️ 1~5 分钟延迟 | MCP Server | 首次需管理员解密 |
| wxlocal watchdog | ✅ PID 轮询 | ✅ 60s + mtime | 导出 JSON | 本项目实现 |

### 6.5 守护进程架构（可选，本项目）

**默认推荐（手动触发）：**

```
登录微信 → 双击 run_extract.bat → output/messages.json 或 Web UI
```

**可选守护进程（不想每次手动双击时）：**

```
Windows 登录
    ↓
任务计划 (setup_autostart.ps1) → run_daemon.bat → watchdog.py
    ↓
轮询 Weixin.exe (每 15s 等待 / 60s 监控)
    ↓
检测到微信 + 数据库 mtime 变化
    ↓
┌─ 有 output/all_keys.json ─→ wcdb-key-tool decrypt → export_messages.py
└─ 无缓存密钥 ─────────────→ wcdb-key-tool extract → decrypt → export
    ↓
output/messages.json 更新
    ↓
（可选）Web UI http://127.0.0.1:8787 查看
```

**守护进程一次性配置步骤（可选）：**

```powershell
# 1. 以管理员运行
cd E:\workspace\wxlocal
.\setup_autostart.ps1

# 2. 验证单次同步
E:\Python312\python.exe watchdog.py --once

# 3. 之后每次：登录 Windows → 打开微信 → 自动同步
```

### 6.6 Windows 启动方案对比

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| **手动双击 run_extract.bat** | 简单、可控、无后台常驻 | 每次需手动触发 | ✅ 默认推荐 |
| **任务计划（登录触发 + 最高权限）** | 自动提权、用户登录即启 | 需一次性 admin 配置、后台常驻 | ⚠️ 可选 |
| **Windows Service (NSSM/wsu)** | 系统级常驻 | SYSTEM 账户看不到用户数据路径 | ❌ |
| **启动文件夹快捷方式** | 简单 | 无管理员权限、控制台闪现 | ❌ |
| **watchdog 内嵌提权** | 自包含 | UAC 弹窗每次 | ❌ |

### 6.7 官方与企业方案

| 方案 | 适用 | 自动化程度 | 限制 |
|------|------|-----------|------|
| **企业微信会话存档 SDK** | 企业微信 | 完全自动 API 拉取 | 需企业资质、管理员开通、私钥配置 |
| **wx4py UI 自动化** | 个人微信 4.x | 可脚本化但需前台窗口 | 无法获取发送者、有封号风险 |
| **WeChat Hook (WeChatFerry 等)** | 旧版微信 | HTTP API 自动推送 | 4.1.13 不支持、高封号风险 |

个人微信 PC 4.1.13 **没有**官方聊天记录读取 API。

---

## 7. 局限性与风险

### 7.1 技术局限

| 局限 | 说明 |
|------|------|
| 版本碎片化 | 每个小版本的 `Weixin.dll` 偏移不同，Hook/断点需重新逆向 |
| 零驻留 | 4.1.10+ 稳态内存无任何密钥痕迹，纯扫描不可能成功 |
| 惰性加载 | 部分 DB 仅在访问对应聊天后才打开，可能暂时无法验证 |
| 图片/语音 | 数据库解密 ≠ 媒体文件解密，图片还需单独的 XOR/AES 密钥 |
| 手机数据 | 手机备份 Backup.db 使用独立密钥，PC 工具无法解密 |
| 多账号 | 每个 wxid 有独立 passphrase，需分别提取 |
| WAL 文件 | 实时消息可能在 `-wal` 中，需额外处理 WAL 帧解密 |

### 7.2 封号与法律风险

| 风险 | 级别 | 说明 |
|------|------|------|
| DLL/Frida 注入 | **中高** | 腾讯可检测注入行为，有真实封号案例（Issue #128, #140） |
| 被动内存读取 | **低** | ReadProcessMemory 不涉及代码注入，相对安全 |
| 调试器附加 | **中** | x64dbg 附加可能被检测 |
| 律师函 | **高** | 多款工具作者收到腾讯律师函后删库（2025-10） |
| 数据隐私 | — | 仅限读取自己的数据；他人聊天记录涉及法律问题 |
| 服务条款 | — | 违反微信用户协议，账号可能被限制 |

**建议：**
- 主号/工作号避免注入类方案
- 优先使用降级提取（方案 B）或被动方案
- 提取后立即断开调试器/卸载 Hook
- passphrase 等同于账号密码，妥善保管

### 7.3 工具生态风险

- 多个 wechat-decrypt fork 已停止维护或收到 DMCA
- GitHub 上部分仓库已被删除（451 Unavailable For Legal Reasons）
- 微信更新频率高（约每 1~2 周一个小版本），工具滞后严重

---

## 8. 未来版本监控清单

当微信升级到 4.1.14+ 或 4.2.x 时，按以下清单检查：

### 8.1 必查项（每次升级后）

- [ ] **passphrase 是否仍有效**：用已有 64 hex 对 `message_0.db` 做 HMAC 验证
- [ ] **加密参数是否变化**：page_size、KDF 迭代次数、HMAC 算法
- [ ] **数据目录是否迁移**：`xwechat_files` 路径或子目录结构变化
- [ ] **Weixin.dll 偏移**：若需 Hook，重新定位 MMV1 / Config.Cipher 函数

### 8.2 关注信号

| 信号 | 来源 | 含义 |
|------|------|------|
| wx-cli / chatlog 新 Issue | GitHub | 社区首次报告新版本问题 |
| wcdb-key-tool 更新 | GitHub Releases | 可能适配了新版本 |
| 微信更新日志 | 官方 | 安全/加密相关更新 |
| Weixin.dll 大小变化 | 本地对比 | 二进制重构信号 |
| `x'96hex'` 模式回归 | 内存扫描 | 不太可能，但可快速检测 |

### 8.3 快速验证脚本

```python
# 保存为 check_version.py，每次升级后运行
import os, struct
from hashlib import pbkdf2_hmac

PASSPHRASE_HEX = "你的64位hex"  # 从安全存储读取
DB = r"D:\app\WeixinData\xwechat_files\sndddepdc_who_29ad\db_storage\message\message_0.db"

with open(DB, "rb") as f:
    page1 = f.read(4096)
salt = page1[:16]
enc_key = pbkdf2_hmac("sha512", bytes.fromhex(PASSPHRASE_HEX), salt, 256000, 32)
# ... HMAC 验证逻辑 ...
print("PASS" if valid else "FAIL - 需要重新提取密钥")
```

### 8.4 版本存档策略

```
1. 保留当前可工作的微信安装包（4.1.13.12）
2. 保留 4.1.9.x 安装包作为降级后备
3. 屏蔽自动更新（hosts 或微信设置）
4. 在 VM 中维护一个「密钥提取专用」环境
5. passphrase 和 all_keys.json 加密备份到离线存储
```

---

## 9. 参考资料

### GitHub Issues / 关键讨论

| 资源 | 内容 |
|------|------|
| [ylytdeng/wechat-decrypt#96](https://github.com/ylytdeng/wechat-decrypt/issues/96) | PBKDF2 passphrase 机制首次完整分析 |
| [ylytdeng/wechat-decrypt#152](https://github.com/ylytdeng/wechat-decrypt/issues/152) | 4.1.10.53 系统性内存分析，确认零驻留 |
| [jackwener/wx-cli#89](https://github.com/jackwener/wx-cli/issues/89) | Windows 4.1.10.27 零候选报告 |
| [jackwener/wx-cli#73](https://github.com/jackwener/wx-cli/issues/73) | macOS 4.1.9 passphrase 问题 |
| [sjzar/chatlog#197](https://github.com/sjzar/chatlog/issues/197) | chatlog FAQ：版本降级方案 |
| [sjzar/chatlog#317](https://github.com/sjzar/chatlog/issues/317) | wx_key + chatlog 配合使用 |

### 工具仓库

| 工具 | URL |
|------|-----|
| wx_key | https://github.com/ycccccccy/wx_key |
| wcdb-key-tool | https://github.com/TANGandXUE/wcdb-key-tool |
| wechat-4.1.12-decrypt | https://github.com/stargazer-2026/wechat-4.1.12-decrypt |
| chatlog | https://github.com/sjzar/chatlog |
| chatlog-keeper | https://github.com/MWH-HEU/chatlog-keeper |
| wetrace | https://github.com/zhizunbao84/wetrace |
| wx-cli | https://github.com/jackwener/wx-cli |
| wechat-decrypt | https://github.com/ylytdeng/wechat-decrypt |
| L1en2407/wechat-decrypt | https://github.com/L1en2407/wechat-decrypt |

### 技术文章

| 文章 | 内容 |
|------|------|
| [wx4.1_analysis.md](https://github.com/ycccccccy/wx_key/blob/main/wx4.1_analysis.md) | 4.1.1.19 setCipherKey 逆向分析 |
| [wener.me/wechat/inside](https://wener.me/notes/platform/wechat/inside) | db_storage 目录结构 |
| [welink/docs/database.md](https://github.com/runzhliu/welink/blob/main/docs/database.md) | 消息表 schema 详解 |
| [xugj520.cn 解密指南](https://www.xugj520.cn/en/archives/wechat-database-decryption-guide.html) | SQLCipher 4 参数说明 |

### 微信版本存档

| 资源 | URL |
|------|-----|
| wechat-windows-versions | https://github.com/cscnk52/wechat-windows-versions |
| WechatWindowsVersionHistory | https://github.com/iibob/WechatWindowsVersionHistory |

---

*本文档由 wxlocal 项目维护，随微信版本更新持续修订。*
