"""F1: mp-scroll enrich retry/backoff/giveup 状态机测试（body + title）。"""
from __future__ import annotations

from datetime import datetime, timedelta

from wxlocal.pipelines.mp_scroll.capture import idb_registry as ir


SN_URL = "https://mp.weixin.qq.com/s?__biz=1&mid=2&idx=3&sn=abc"


def _row(**kw) -> dict:
    """构建一条 registry 行，含 F1 字段默认值。"""
    defaults = {
        "url": SN_URL,
        "article_key": "k1",
        "url_kind": "full",
        "first_seen": (datetime.now() - timedelta(hours=100)).isoformat(),
        "last_seen": (datetime.now() - timedelta(hours=100)).isoformat(),
        "seen_count": 1,
        "title": "Some Title",
        "summary": "",
        "source_name": "src",
        "status": "discovered",
        "marked": False,
        "body": "",
        "fetched_at": None,
        "body_attempts": 0,
        "body_giveup": False,
        "title_attempts": 0,
        "title_giveup": False,
    }
    defaults.update(kw)
    return defaults


def _reg(items: dict) -> dict:
    return {"meta": {}, "items": {str(k): v for k, v in items.items()}}


# --- _in_backoff_window ---


def test_in_backoff_window_zero_attempts_never_in_window():
    row = {"first_seen": datetime(2026, 9, 2, 6, 0, 0).isoformat()}
    now = datetime(2026, 9, 2, 6, 1, 0)
    assert ir._in_backoff_window(row, 0, 6, now) is False


def test_in_backoff_window_boundary_exactly_equal_is_outside():
    """elapsed == attempts*hours → 窗口已到期，可重试。"""
    first = datetime(2026, 9, 2, 6, 0, 0)
    row = {"first_seen": first.isoformat()}
    now = first + timedelta(hours=6)
    assert ir._in_backoff_window(row, 1, 6, now) is False  # 1*6h 到期


def test_in_backoff_window_inside_window():
    first = datetime(2026, 9, 2, 6, 0, 0)
    row = {"first_seen": first.isoformat()}
    now = first + timedelta(hours=5)  # 1*6h 窗口内（5h<6h）
    assert ir._in_backoff_window(row, 1, 6, now) is True


def test_in_backoff_window_outside_window():
    first = datetime(2026, 9, 2, 6, 0, 0)
    row = {"first_seen": first.isoformat()}
    now = first + timedelta(hours=24)  # 远超 1*6h
    assert ir._in_backoff_window(row, 1, 6, now) is False


def test_in_backoff_window_missing_first_seen_is_outside():
    assert ir._in_backoff_window({"first_seen": ""}, 3, 6, datetime.now()) is False
    assert ir._in_backoff_window({}, 3, 6, datetime.now()) is False


# --- enrich_body_pending ---


def test_body_enrich_legacy_rows_one_time_giveup(monkeypatch):
    """存量历史积压行（无 body_attempts 键）首次跑一次性置 body_giveup。"""
    monkeypatch.setattr(ir, "fetch_http_body", lambda url, opener: "")
    row = _row(status="discovered")
    row.pop("body_attempts")
    row.pop("body_giveup")
    reg = _reg({"u1": row})
    stats = ir.enrich_body_pending(reg, now=datetime.now())
    assert stats["fetched"] == 0
    assert stats["bodies"] == 0
    assert stats["failed"] == 0
    assert stats["giveup"] == 1
    assert reg["items"]["u1"]["body_giveup"] is True


def test_body_enrich_skips_already_given_up(monkeypatch):
    """已标记 body_giveup 的行永不再重试。"""
    monkeypatch.setattr(ir, "fetch_http_body", lambda url, opener: "x" * 200)
    row = _row(status="title_fetched", body_attempts=5, body_giveup=True)
    reg = _reg({"u1": row})
    stats = ir.enrich_body_pending(reg, now=datetime.now())
    assert stats["fetched"] == 0
    assert stats["failed"] == 0


def test_body_enrich_success_resets_attempts_and_clears_giveup(monkeypatch):
    """正文抓取成功后重置 body_attempts=0 并清除 body_giveup。"""
    monkeypatch.setattr(ir, "fetch_http_body", lambda url, opener: "x" * 200)
    # 行有 body_attempts 但无 body_giveup（仍在重试中），成功后进攻清零
    row = _row(status="title_fetched", body_attempts=3)
    reg = _reg({"u1": row})
    stats = ir.enrich_body_pending(reg, now=datetime.now())
    assert stats["bodies"] == 1
    assert stats["failed"] == 0
    assert reg["items"]["u1"]["body_attempts"] == 0
    assert "body_giveup" not in reg["items"]["u1"]


def test_body_enrich_failure_increments_attempts(monkeypatch):
    """正文抓取失败累加 body_attempts。"""
    monkeypatch.setattr(ir, "fetch_http_body", lambda url, opener: "")
    row = _row(status="title_fetched", body_attempts=2)
    reg = _reg({"u1": row})
    stats = ir.enrich_body_pending(reg, now=datetime.now())
    assert stats["failed"] == 1
    assert reg["items"]["u1"]["body_attempts"] == 3
    assert reg["items"]["u1"]["body_giveup"] is False


def test_body_enrich_failure_at_max_sets_giveup(monkeypatch):
    """失败达到上限时置 body_giveup=True。"""
    monkeypatch.setattr(ir, "fetch_http_body", lambda url, opener: "")
    # max 默认 5；attempts=4 → 本次后达 5 → giveup
    row = _row(status="title_fetched", body_attempts=4)
    reg = _reg({"u1": row})
    stats = ir.enrich_body_pending(reg, now=datetime.now())
    assert stats["failed"] == 1
    assert reg["items"]["u1"]["body_attempts"] == 5
    assert reg["items"]["u1"]["body_giveup"] is True


def test_body_enrich_backoff_window_skips_in_window_rows(monkeypatch):
    """退避窗口内的行被跳过，计入 backoff_skipped。"""
    monkeypatch.setattr(ir, "fetch_http_body", lambda url, opener: "x" * 200)
    old = datetime(2026, 9, 2, 6, 0, 0)
    row = _row(first_seen=old.isoformat(), status="title_fetched", body_attempts=2)
    reg = _reg({"u1": row})
    now = old + timedelta(hours=2)  # 2*6=12h，仅过 2h → 窗口内
    stats = ir.enrich_body_pending(reg, now=now)
    assert stats["fetched"] == 0
    assert stats["backoff_skipped"] == 1


def test_body_enrich_backoff_window_expired_allows_retry(monkeypatch):
    """退避窗口到期的行允许重试。"""
    monkeypatch.setattr(ir, "fetch_http_body", lambda url, opener: "x" * 200)
    old = datetime(2026, 9, 2, 6, 0, 0)
    row = _row(first_seen=old.isoformat(), status="title_fetched", body_attempts=2)
    reg = _reg({"u1": row})
    now = old + timedelta(hours=13)  # 2*6=12h，已过 13h → 窗口外
    stats = ir.enrich_body_pending(reg, now=now)
    assert stats["fetched"] == 1
    assert stats["bodies"] == 1
    assert stats["backoff_skipped"] == 0


def test_body_enrich_batch_limit_respected(monkeypatch):
    """批量上限被遵守。"""
    monkeypatch.setattr(ir, "fetch_http_body", lambda url, opener: "x" * 200)
    rows = {
        f"u{i}": _row(
            status="title_fetched",
            article_key=f"k{i}",
            url=f"https://mp.weixin.qq.com/s?__biz=1&mid=2&idx={i}&sn=s{i}",
        )
        for i in range(10)
    }
    reg = _reg(rows)
    stats = ir.enrich_body_pending(reg, limit=3, now=datetime.now())
    assert stats["fetched"] == 3
    assert stats["bodies"] == 3


# --- enrich_pending (title, symmetric) ---


def test_title_enrich_success_resets_attempts(monkeypatch):
    """标题抓取成功后重置 title_attempts=0 并清除 title_giveup。"""
    monkeypatch.setattr(ir, "fetch_title_from_page", lambda url, opener: ("New Title", ""))
    row = _row(title="", status="discovered", title_attempts=2)
    reg = _reg({"u1": row})
    stats = ir.enrich_pending(reg, now=datetime.now())
    assert stats["titles"] == 1
    assert reg["items"]["u1"]["title"] == "New Title"
    assert reg["items"]["u1"]["title_attempts"] == 0
    assert "title_giveup" not in reg["items"]["u1"]


def test_title_enrich_failure_giveup_at_max(monkeypatch):
    """标题抓取失败累计，达上限（3）置 title_giveup。"""
    monkeypatch.setattr(ir, "fetch_title_from_page", lambda url, opener: ("", ""))
    row = _row(title="", status="title_failed", title_attempts=2)  # max=3
    reg = _reg({"u1": row})
    stats = ir.enrich_pending(reg, now=datetime.now())
    assert stats["failed"] == 1
    assert reg["items"]["u1"]["title_attempts"] == 3
    assert reg["items"]["u1"]["title_giveup"] is True


def test_title_enrich_backoff_window_skips(monkeypatch):
    """标题退避窗口内的行被跳过。"""
    monkeypatch.setattr(ir, "fetch_title_from_page", lambda url, opener: ("Title", ""))
    old = datetime(2026, 9, 2, 6, 0, 0)
    row = _row(title="", status="discovered", first_seen=old.isoformat(), title_attempts=2)
    reg = _reg({"u1": row})
    now = old + timedelta(hours=2)  # 2*6=12h，仅过 2h → 窗口内
    stats = ir.enrich_pending(reg, now=now)
    assert stats["fetched"] == 0
    assert stats["backoff_skipped"] == 1


def test_title_enrich_skips_already_given_up(monkeypatch):
    """已 title_giveup 的行不再重试。"""
    monkeypatch.setattr(ir, "fetch_title_from_page", lambda url, opener: ("Title", ""))
    row = _row(title="", status="title_failed", title_attempts=3, title_giveup=True)
    reg = _reg({"u1": row})
    stats = ir.enrich_pending(reg, now=datetime.now())
    assert stats["fetched"] == 0
    assert stats["titles"] == 0


def test_title_enrich_no_title_no_body_fetch_does_not_break(monkeypatch):
    """标题失败且无正文时，行保持 title_failed 且 body 为空。"""
    monkeypatch.setattr(ir, "fetch_title_from_page", lambda url, opener: ("", ""))
    row = _row(title="", status="discovered", title_attempts=0)
    reg = _reg({"u1": row})
    stats = ir.enrich_pending(reg, now=datetime.now())
    assert stats["failed"] == 1
    assert reg["items"]["u1"]["status"] == "title_failed"
    assert reg["items"]["u1"].get("body", "") == ""