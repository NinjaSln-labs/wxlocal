# wxlocal 后续路线图

> 2026-08-30 调研定稿。前置状态：R0–R10 / Phase A–D 全部完成（v0.2.0），无进行中任务。
> 执行规则沿用 [DEV_PLAN.md](DEV_PLAN.md)：先计划 → 实现 → `.\scripts\verify.ps1` 通过 → 再 commit/push。

## 调研结论（2026-08-30 实测）

1. **mp 正文抓取自 2026-08-28 22:22 起全灭，原因不是代理。**
   注册表 175 条正文全部产自 08-27 18:05 ~ 08-28 22:22；此后零成功。`WECHAT_FETCH_PROXY`(6696) 实测连通。
   真实原因：微信对所有 UA（桌面 / iPhone / Android 均实测）返回 ~2.3MB 纯 JS 渲染页——无 `js_content` div、无 SSR 正文、`<title>` 为空；正文改由客户端 XHR（页面可见 `/mp/getappmsgext` 系列接口）按会话拉取。`body_extract.py` 六层正则全部落空。
   ⇒ HANDOFF 旧提示「查代理」为误诊。
2. **enrich 重试缺陷在放大问题**：每轮（约 57s）重试同一批 15 条失败 URL，无退避、无上限、日志每分钟刷 `failed=15`；有触发风控的风险。
3. **OCR 是现成开关**：`MP_SCROLL_OCR=1` + `.[ocr]`（rapidocr-onnxruntime），默认每 8 轮截屏识别推荐流卡片标题。
4. **mitm 管道有地基**：`capture/addon.py` + `parsers.py` 已能拦截响应并提取文章 URL/标题，但目前只采元数据、不采正文。
5. **chat-watch delta 适合接全文**：`delta.json` 每条卡片带 `title / url(sn) / summary / time`。

## 路线图

### F1 · 止血：enrich 重试机制（P0 · ~0.5 天）

- body enrich 加失败退避：`attempts` 计数 + 指数退避 + 上限（5 次后标记 `body_giveup` 不再重试）；跳过无 `sn` 的 URL。
- 验收：`verify.ps1` 全绿；日志不再每轮重复同一批失败 URL。

### F2 · 正文抓取恢复（P0 · 2–4 天 · 核心攻坚）

| 路线 | 说明 | 结论 |
|------|------|------|
| **A（推荐）** | 扩展 mitm addon：用户点开文章时拦截正文 XHR 响应，提取正文写回注册表 | 地基全在（`_is_high_value` 已识别高价值响应）；零新依赖；天然只抓"真点开过"的文章 |
| B（备选） | 从 WeChatAppEx 配置取会话 cookie 模拟 XHR | 可自动化但参数脆弱、有风控风险；作 A 的补充验证 |
| C | headless 浏览器渲染 | 依赖重、性能差，不采用 |

- 存量清理：301 条无正文 URL 一次性判定，08-28 前的旧链接大概率永久抓不到，标记归档。
- 验收：点开 10 篇 → 注册表 body 新增 ≥10，`fetched_at` 更新。

### F3 · OCR 标题扩量（P1 · ~0.5 天）

- `pip install ".[ocr]"` + `MP_SCROLL_OCR=1`，跑 24h 观察 `ocr_new` 增量与 CPU 占用，再决定是否常开。
- 可回退：关开关即回现状。

### F4 · NinjaSin 全文补全（P2 · 1–2 天 · 新产品能力 · 依赖 F2）

- 新流水线 `chat_watch fulltext`：消费 `delta.json` 卡片 URL → 复用 F2 正文抓取 → 产出 `delta_full.json` / `delta_full.md` 与现有 delta 并列。
- 立项前需确认：① 覆盖联系人范围（仅 NinjaSin?）；② 问津侧期望的消费格式。

### F5 · 前瞻维护（P3 · 持续）

- 微信客户端升级后的兼容检查（[WECHAT_4.1.13_RESEARCH.md](WECHAT_4.1.13_RESEARCH.md) 清单）。
- 仓库搬家后必须重装 editable（见本地 HANDOFF-ARCHIVE/pits.md）。
- T2/T3 集成测试加「正文成功率 > 0」断言，防再次静默失效。

## 启动顺序

**F1 → F2(路线 A) → F3**；三步完成后评审是否立项 F4。F1/F3 无决策依赖；F2 路线 A 验证需人工配合点开文章。
