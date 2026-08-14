from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from robjy.config import AppConfig

logger = logging.getLogger(__name__)


class SessionExpiredError(RuntimeError):
    """会话失效，需要重新手动授权。"""


class BrowserSession:
    """Playwright 浏览器会话：手动登录导出 / 注入复用 / 登录态探测。"""

    AUTH_HINTS = ("医保卡", "换卡", "个人中心", "门诊服务", "门诊预约")

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self.page: Any = None

    def __enter__(self) -> BrowserSession:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._context is not None:
            try:
                self._context.close()
            except Exception:  # noqa: BLE001
                logger.debug("关闭 context 时忽略异常", exc_info=True)
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:  # noqa: BLE001
                logger.debug("关闭 browser 时忽略异常", exc_info=True)
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:  # noqa: BLE001
                logger.debug("停止 playwright 时忽略异常", exc_info=True)
        self._context = None
        self._browser = None
        self._playwright = None
        self.page = None

    def _launch_browser(self, *, headless: bool | None = None) -> None:
        from playwright.sync_api import sync_playwright

        if self._playwright is None:
            self._playwright = sync_playwright().start()

        use_headless = self.config.session.headless if headless is None else headless
        self._browser = self._playwright.chromium.launch(headless=use_headless)

    def _new_context(self, *, storage_state: str | Path | None = None) -> None:
        assert self._browser is not None
        kwargs: dict[str, Any] = {
            "user_agent": self.config.runtime.user_agent,
            "viewport": self.config.runtime.viewport,
            "locale": "zh-CN",
            "timezone_id": self.config.scheduler.timezone,
            "is_mobile": True,
            "has_touch": True,
        }
        if storage_state is not None:
            kwargs["storage_state"] = str(storage_state)
        self._context = self._browser.new_context(**kwargs)
        self.page = self._context.new_page()
        self.page.set_default_timeout(self.config.booking.step_timeout_ms)

    def login_interactive(self, wait_sec: int = 180) -> Path:
        """有头打开入口，等待人工完成微信授权，导出 storage_state。"""
        state_path = self.config.state_path
        state_path.parent.mkdir(parents=True, exist_ok=True)

        self._launch_browser(headless=False)
        self._new_context()
        assert self.page is not None

        logger.info("打开 H5 入口，请在浏览器中完成微信授权: %s", self.config.site.entry_url)
        self.page.goto(self.config.site.entry_url, wait_until="domcontentloaded")

        deadline = time.time() + wait_sec
        while time.time() < deadline:
            if self.is_authenticated(strict=False):
                self._context.storage_state(path=str(state_path))
                logger.info("已检测到登录态，会话已保存: %s", state_path)
                return state_path
            time.sleep(1.5)

        # 超时仍尝试导出，便于排障；同时提示失败
        self._context.storage_state(path=str(state_path))
        raise SessionExpiredError(
            f"在 {wait_sec}s 内未检测到登录态。请重新执行 login，并确认微信授权成功。"
            f" 已写出当前 state 供检查: {state_path}"
        )

    def open_with_state(self, *, headless: bool | None = None) -> None:
        """注入已有 storage_state 并打开入口。"""
        state_path = self.config.state_path
        if not state_path.exists():
            raise FileNotFoundError(
                f"会话文件不存在: {state_path}。请先运行: python scripts/grab.py login -c <config>"
            )

        self._launch_browser(headless=headless)
        self._new_context(storage_state=state_path)
        assert self.page is not None
        logger.info("注入会话并打开入口: %s", self.config.site.entry_url)
        self.page.goto(self.config.site.entry_url, wait_until="domcontentloaded")

    def ensure_authenticated(self) -> None:
        timeout = self.config.session.auth_timeout_sec
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_authenticated(strict=True):
                logger.info("登录态有效")
                return
            time.sleep(0.8)
        raise SessionExpiredError(
            "会话已失效或未登录。请重新执行: python scripts/grab.py login -c config/local.yaml"
        )

    def is_authenticated(self, *, strict: bool = True) -> bool:
        """通过首页文案信号判断是否已登录。"""
        if self.page is None:
            return False
        try:
            content = self.page.content()
        except Exception:  # noqa: BLE001
            return False

        # 明显未登录 / 授权页
        deny_markers = ("网页授权", "微信登录", "scope.userInfo", "请在微信客户端打开")
        if any(m in content for m in deny_markers):
            return False

        hits = sum(1 for h in self.AUTH_HINTS if h in content)
        if strict:
            return hits >= 2
        return hits >= 1

    def save_state(self) -> Path:
        if self._context is None:
            raise RuntimeError("无可用 context，无法保存会话")
        path = self.config.state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._context.storage_state(path=str(path))
        return path
