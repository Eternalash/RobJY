from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from robjy.config import load_config
from robjy.scheduler.release import ReleaseScheduler
from robjy.config import (
    AppConfig,
    BookingConfig,
    RuntimeConfig,
    SchedulerConfig,
    SessionConfig,
    SiteConfig,
)
from robjy.session.browser import BrowserSession


def test_load_example_config():
    cfg = load_config(Path("config/example.yaml"))
    assert cfg.site.customer_id == "94"
    assert cfg.booking.campus_priority[0] == "南部院区"
    assert cfg.booking.title_priority[0] == "主任医师"
    assert cfg.scheduler.release_time == "07:30:00"
    assert cfg.booking.confirm_submit is True


def test_today_release_at_parses():
    cfg = AppConfig(
        site=SiteConfig(entry_url="https://example.com"),
        session=SessionConfig(),
        booking=BookingConfig(),
        scheduler=SchedulerConfig(timezone="Asia/Shanghai", release_time="07:30:00"),
        runtime=RuntimeConfig(),
    )
    sched = ReleaseScheduler(cfg, BrowserSession(cfg))
    release = sched._today_release_at()
    assert release.tzinfo == ZoneInfo("Asia/Shanghai")
    assert release.hour == 7 and release.minute == 30 and release.second == 0
    assert isinstance(release, datetime)
