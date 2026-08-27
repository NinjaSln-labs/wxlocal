"""抓包目标域名与 URL 模式。"""
from __future__ import annotations

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
