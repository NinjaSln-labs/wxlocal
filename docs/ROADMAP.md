# wxlocal 后续路线图

> 2026-08-30 调研定稿。前置状态：R0–R10 / Phase A–D 全部完成（v0.2.0），无进行中任务。
> 执行规则沿用 [DEV_PLAN.md](DEV_PLAN.md)：先计划 → 实现 → `.\scripts\verify.ps1` 通过 → 再 commit/push。

## 调研结论（2026-08-30 实测）

1. **mp 正文抓取自 2026-08-28 22:22 起全灭，原因不是代理。**
   注册表 175 条正文全部产自 08-27 18:05 ~ 08-28 22:22；此后零成功。`WECHAT_FETCH_PROXY`(6696) 实测连通。
   08-30 初查结论：微信对桌面 UA 返回 ~2.3MB 纯 JS 渲染页，正文走客户端 XHR。

   **09-02 抓包实验修正（证伪上一条）**：微信 PC 客户端正文**不走 HTTP**，走 **mmsocket**（私有加密二进制协议）直连腾讯内网 IP（`101.226.144.240`），**绕过 HTTP 代理**，mitm 抓不到。HTTP GET 文章 URL 现返回**腾讯验证码（TCaptcha）挑战页**（`captcha.gtimg.com/TCaptcha.js` + `window.cgiData`），非 JS 壳。两条线（chat-watch 卡片 + mp-scroll URL）拿文章全文都依赖 HTTP，HTTP 堵死则全文拿不到。
2. **enrich 重试缺陷在放大问题**：每轮（约 57s）重试同一批 15 条失败 URL，无退避、无上限、日志每分钟刷 `failed=15`；有触发风控的风险。
3. **OCR 是现成开关**：`MP_SCROLL_OCR=1` + `.[ocr]`（rapidocr-onnxruntime），默认每 8 轮截屏识别推荐流卡片标题。
4. **mitm 管道有地基**：`capture/addon.py` + `parsers.py` 已能拦截响应并提取文章 URL/标题，但目前只采元数据、不采正文。
5. **chat-watch delta 适合接全文**：`delta.json` 每条卡片带 `title / url(sn) / summary / time`。

## 路线图

### F1 · 止血：enrich 重试机制（P0 · ~0.5 天）

- body enrich 加失败退避：`attempts` 计数 + 指数退避 + 上限（5 次后标记 `body_giveup` 不再重试）；跳过无 `sn` 的 URL。
- 验收：`verify.ps1` 全绿；日志不再每轮重复同一批失败 URL。

### F2 · 正文抓取恢复（P0 · 核心攻坚 · 待方案验证）

微信客户端正文走 mmsocket 加密直连，绕过 HTTP 代理。HTTP GET 文章 URL 现被验证码（TCaptcha）拦截。两条线（chat-watch/mp-scroll）拿文章全文都依赖 HTTP，HTTP 堵死。

| 路线 | 说明 | 状态 |
|------|------|------|
| **A（验证码 API 破解，推荐）** | 注册 2Captcha / CapSolver 付费 API；`urllib` 拿验证码 → API 解题 → 过码拿正文 → `backfill_body` 写回 | 待注册 API 验证 |
| B（桌面浏览器 Playwright） | 半自动，需用户开浏览器点或 Playwright 模拟；走 8848 代理拦正文 | 待验证 |
| C（mmsocket 逆向） | 私有加密二进制协议，成本极高，随客户端版本脆弱 | 不采用 |
| D（放弃全自动） | 保留标题+摘要，正文靠手动 | 保底 |

- 写回管道 `backfill_body`（[0400ea4]）+ URL/article_key 匹配已就位；存量 19 条有 sn 无正文行待刷
- 验收：批量 10 篇 → 注册表 body 新增 ≥10，`fetched_at` 更新

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

**已完成：F1（正文 enrich 退避）**；**F3（OCR 标题扩量）用户取消不开**。
**进行中：F2（正文恢复）→ 待验证码 API 破解方案验证后再开工。**

F2 路线 A（验证码 API）验证通过后再评审是否立项 F4。
