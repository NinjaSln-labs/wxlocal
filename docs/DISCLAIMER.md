# 免责声明 / Disclaimer

> **请先阅读。** 使用、复制或修改本仓库任何代码，即表示你已理解并自行承担下列风险。

## 用途说明

本仓库为 **个人自学习、技术研究** 用途而整理，旨在帮助开发者了解：

- 本地客户端如何存储加密数据库；
- 如何在 **本人设备、本人账号、本人数据** 的前提下做离线分析与导出实验。

**不是** 腾讯微信官方产品，**不提供** 任何商业服务、数据恢复服务或「破解他人聊天记录」能力。

## 合规与法律风险

1. **微信用户协议与服务条款**  
   微信 PC / 移动端用户协议通常禁止对客户端进行未授权的逆向、抓包、绕过安全机制等行为。本仓库涉及读取微信 **内部本地数据**（含 WCDB 解密、IndexedDB、可选 mitm 抓包等），可能与平台规则冲突。

2. **隐私与数据保护**  
   聊天记录、联系人、订阅号浏览记录等属于 **个人敏感信息**。你应：
   - 仅处理 **自己账号** 或 **已获明确授权** 的数据；
   - 不得用于窃取、传播、贩卖他人隐私；
   - 遵守《个人信息保护法》及你所在司法辖区的 applicable 法律。

3. **法规因地区而异**  
   作者 **不对** 你在特定国家/地区使用本工具是否合法做任何保证。使用前请自行咨询法律意见，**自行评估合规风险**。

## 技术限制与不保证可用性

- 微信版本更新频繁，加密策略、存储路径、IndexedDB 结构 **随时可能变更**；
- 本仓库 **不保证** 在任何微信版本、任何 Windows 环境上可用；
- 功能按 **「现状提供」(AS IS)** 发布，**无** 适销性、特定用途适用性担保；
- 可能导致微信异常、数据损坏、账号限制等，**风险自负**。

## 你需要自行调整的内容

| 项目 | 说明 |
|------|------|
| 数据目录 | 在 `.env` 中设置 `WECHAT_DATA_ROOT`、`WECHAT_KB_ROOT` |
| 监控联系人 | `WECHAT_WATCH_CONTACT` 按你的实际需求配置 |
| 代理 / 抓包 | 是否启用 mitm、是否使用 HTTP 代理，由你自行决定 |
| 自启动 | 登录启动项、计划任务等，请只在可信环境启用 |
| 密钥提取 | 内存扫描等方式可能需要管理员权限，请知悉安全风险 |

**请勿** 将本仓库中的示例路径、示例联系人名当作可直接用于生产的配置。

## 作者责任限制

在法律允许的最大范围内，作者及贡献者 **不对** 因使用本软件导致的任何直接、间接、附带、特殊或后果性损害承担责任，包括但不限于：数据丢失、业务中断、账号封禁、法律纠纷。

MIT License 中的免责条款同样适用，见 [LICENSE](../LICENSE)。

---

## English summary

This project is for **personal learning and technical research** on **your own** WeChat PC local data only. It is **not** affiliated with Tencent WeChat. Use may conflict with WeChat's Terms of Service. **No warranty** of fitness or continued compatibility. **You** are solely responsible for legality, privacy compliance, and configuring paths/contacts/proxies for your environment. Authors disclaim liability for damages arising from use.

**If you do not agree, do not use this software.**
