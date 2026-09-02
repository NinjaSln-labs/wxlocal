"""抓包目标域名、URL 模式与 enrich 重试/退避常量。"""
from __future__ import annotations

import os
import re

# 微信 PC 订阅号 / 文章 / 推荐流相关主机
CAPTURE_HOSTS = (
    "weixin.qq.com",       # 含 mp. / szextshort. / open. 等子域
    "weixinbridge.com",
    "qpic.cn",
    "wx.qq.com",
)

# 高价值路径（文章页 / 推荐流 API）
HIGH_VALUE_PATH_RE = re.compile(
    r"/s[\?/]|/mp/|getappmsg|profile_ext|masssend|appmsg|timeline|feed|recommend",
    re.I,
)

# 文章链接
ARTICLE_URL_RE = re.compile(
    r"https?://mp\.weixin\.qq\.com/s[^\s\"'<>]*|"
    r"https?://mp\.weixin\.qq\.com/mp/[^\s\"'<>]*",
    re.I,
)

# 归一化文章 URL 时保留的 query 键
URL_KEEP_KEYS = ("__biz", "mid", "idx", "sn", "chksm")

# --- enrich 重试与退避（F1）---
# body enrich: 失败累加达上限后 body_giveup，线性退避基于 first_seen
MP_SCROLL_BODY_MAX_ATTEMPTS = int(os.environ.get("MP_SCROLL_BODY_MAX_ATTEMPTS", "5"))
MP_SCROLL_BODY_BACKOFF_HOURS = int(os.environ.get("MP_SCROLL_BODY_BACKOFF_HOURS", "6"))
# title enrich: 对称机制，上限 3、退避 6h
MP_SCROLL_TITLE_MAX_ATTEMPTS = int(os.environ.get("MP_SCROLL_TITLE_MAX_ATTEMPTS", "3"))
MP_SCROLL_TITLE_BACKOFF_HOURS = int(os.environ.get("MP_SCROLL_TITLE_BACKOFF_HOURS", "6"))
