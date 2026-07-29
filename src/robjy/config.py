from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CAMPUS_PRIORITY = ["南部院区", "高科园区"]
DEFAULT_TITLE_PRIORITY = ["主任医师", "副主任医师"]


@dataclass
class SiteConfig:
    entry_url: str
    customer_id: str = "94"
    ui_service_id: str = "gh_79eafca4e31a"


@dataclass
class SessionConfig:
    state_path: str = ".data/storage_state.json"
    headless: bool = False
    auth_timeout_sec: int = 30


@dataclass
class BookingConfig:
    department_category: str = ""
    department: str = ""
    patient_name: str = ""
    campus_priority: list[str] = field(default_factory=lambda: list(DEFAULT_CAMPUS_PRIORITY))
    title_priority: list[str] = field(default_factory=lambda: list(DEFAULT_TITLE_PRIORITY))
    department_match: str = "contains"  # exact | contains
    confirm_submit: bool = True
    step_timeout_ms: int = 15000


@dataclass
class SchedulerConfig:
    timezone: str = "Asia/Shanghai"
    release_time: str = "07:30:00"
    warmup_lead_sec: int = 120
    poll_window_sec: int = 180
    poll_interval_sec: float = 0.5
    max_attempts: int = 240


@dataclass
class RuntimeConfig:
    artifact_dir: str = ".data/artifacts"
    captcha_dir: str = ".data/captcha"
    user_agent: str = (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Version/4.0 Chrome/120.0.0.0 Mobile Safari/537.36 "
        "MicroMessenger/8.0.44"
    )
    viewport: dict[str, int] = field(default_factory=lambda: {"width": 390, "height": 844})


@dataclass
class AppConfig:
    site: SiteConfig
    session: SessionConfig = field(default_factory=SessionConfig)
    booking: BookingConfig = field(default_factory=BookingConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)

    @property
    def state_path(self) -> Path:
        return Path(self.session.state_path)

    @property
    def artifact_dir(self) -> Path:
        return Path(self.runtime.artifact_dir)

    @property
    def captcha_dir(self) -> Path:
        return Path(self.runtime.captcha_dir)


def _require(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"配置缺少必填项: {key}")
    return data[key]


def load_config(path: str | Path) -> AppConfig:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {cfg_path}")

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    site_raw = _require(raw, "site")
    session_raw = raw.get("session") or {}
    booking_raw = raw.get("booking") or {}
    scheduler_raw = raw.get("scheduler") or {}
    runtime_raw = raw.get("runtime") or {}

    site = SiteConfig(
        entry_url=str(_require(site_raw, "entry_url")),
        customer_id=str(site_raw.get("customer_id", "94")),
        ui_service_id=str(site_raw.get("ui_service_id", "gh_79eafca4e31a")),
    )
    session = SessionConfig(
        state_path=str(session_raw.get("state_path", ".data/storage_state.json")),
        headless=bool(session_raw.get("headless", False)),
        auth_timeout_sec=int(session_raw.get("auth_timeout_sec", 30)),
    )
    booking = BookingConfig(
        department_category=str(booking_raw.get("department_category", "")),
        department=str(booking_raw.get("department", "")),
        patient_name=str(booking_raw.get("patient_name", "")),
        campus_priority=list(booking_raw.get("campus_priority") or DEFAULT_CAMPUS_PRIORITY),
        title_priority=list(booking_raw.get("title_priority") or DEFAULT_TITLE_PRIORITY),
        department_match=str(booking_raw.get("department_match", "contains")),
        confirm_submit=bool(booking_raw.get("confirm_submit", True)),
        step_timeout_ms=int(booking_raw.get("step_timeout_ms", 15000)),
    )
    scheduler = SchedulerConfig(
        timezone=str(scheduler_raw.get("timezone", "Asia/Shanghai")),
        release_time=str(scheduler_raw.get("release_time", "07:30:00")),
        warmup_lead_sec=int(scheduler_raw.get("warmup_lead_sec", 120)),
        poll_window_sec=int(scheduler_raw.get("poll_window_sec", 180)),
        poll_interval_sec=float(scheduler_raw.get("poll_interval_sec", 0.5)),
        max_attempts=int(scheduler_raw.get("max_attempts", 240)),
    )
    runtime = RuntimeConfig(
        artifact_dir=str(runtime_raw.get("artifact_dir", ".data/artifacts")),
        captcha_dir=str(runtime_raw.get("captcha_dir", ".data/captcha")),
        user_agent=str(runtime_raw.get("user_agent") or RuntimeConfig().user_agent),
        viewport=dict(runtime_raw.get("viewport") or {"width": 390, "height": 844}),
    )
    return AppConfig(
        site=site,
        session=session,
        booking=booking,
        scheduler=scheduler,
        runtime=runtime,
    )
