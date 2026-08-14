from __future__ import annotations

from robjy.config import (
    AppConfig,
    BookingConfig,
    RuntimeConfig,
    SchedulerConfig,
    SessionConfig,
    SiteConfig,
)
from robjy.session.browser import BrowserSession


def _cfg() -> AppConfig:
    return AppConfig(
        site=SiteConfig(entry_url="https://example.com"),
        session=SessionConfig(),
        booking=BookingConfig(),
        scheduler=SchedulerConfig(),
        runtime=RuntimeConfig(),
    )


class _FakePage:
    def __init__(self, html: str) -> None:
        self._html = html

    def content(self) -> str:
        return self._html


def test_is_authenticated_strict_requires_multiple_hints():
    session = BrowserSession(_cfg())
    session.page = _FakePage("<div>门诊预约 个人中心 医保卡 换卡</div>")
    assert session.is_authenticated(strict=True) is True


def test_is_authenticated_false_on_oauth_page():
    session = BrowserSession(_cfg())
    session.page = _FakePage("<div>网页授权 微信登录 scope.userInfo</div>")
    assert session.is_authenticated(strict=True) is False


def test_is_authenticated_false_when_signals_insufficient():
    session = BrowserSession(_cfg())
    session.page = _FakePage("<div>技术支持：上海齐脉</div>")
    assert session.is_authenticated(strict=True) is False
