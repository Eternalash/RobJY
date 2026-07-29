from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable

from robjy.adapters.shqmxx.pages import ShqmxxAdapter
from robjy.config import AppConfig
from robjy.priority.policy import PriorityPolicy
from robjy.session.browser import BrowserSession

logger = logging.getLogger(__name__)


class FlowState(str, Enum):
    AUTH_READY = "AuthReady"
    HOME = "Home"
    NOTICE = "Notice"
    CAMPUS_SELECT = "CampusSelect"
    DEPT_SELECT = "DeptSelect"
    DOCTOR_DATE = "DoctorDate"
    TIME_SLOT = "TimeSlot"
    PATIENT_CONFIRM = "PatientConfirm"
    CAPTCHA = "Captcha"
    SUBMITTED = "Submitted"
    FAILED = "Failed"
    NO_SLOT = "NoSlot"


@dataclass
class BookingResult:
    ok: bool
    state: FlowState
    message: str
    campus: str | None = None
    doctor: str | None = None
    artifacts: list[str] = field(default_factory=list)


CaptchaProvider = Callable[[Path], str]


def stdin_captcha_provider(shot_path: Path) -> str:
    print(f"请查看验证码截图: {shot_path}")
    return input("请输入验证码: ").strip()


class BookingFlow:
    """门诊预约状态机。"""

    def __init__(
        self,
        config: AppConfig,
        session: BrowserSession,
        *,
        captcha_provider: CaptchaProvider | None = None,
        stop_before_captcha: bool = False,
    ) -> None:
        self.config = config
        self.session = session
        self.policy = PriorityPolicy(
            campus_priority=config.booking.campus_priority,
            title_priority=config.booking.title_priority,
        )
        self.captcha_provider = captcha_provider or stdin_captcha_provider
        self.stop_before_captcha = stop_before_captcha
        self.state = FlowState.AUTH_READY
        self.artifact_dir = config.artifact_dir
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self._artifacts: list[str] = []
        self._adapter: ShqmxxAdapter | None = None
        self._selected_campus: str | None = None
        self._selected_doctor: str | None = None

    @property
    def adapter(self) -> ShqmxxAdapter:
        if self._adapter is None:
            if self.session.page is None:
                raise RuntimeError("BrowserSession.page 未初始化")
            self._adapter = ShqmxxAdapter(self.session.page, self.config, self.policy)
        return self._adapter

    def _shot(self, step: str) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self.artifact_dir / f"{ts}_{step}.png"
        try:
            self.adapter.screenshot(path)
            self._artifacts.append(str(path))
            logger.info("截图: %s", path)
        except Exception:  # noqa: BLE001
            logger.warning("截图失败: %s", step, exc_info=True)
        return path

    def _fail(self, message: str) -> BookingResult:
        self.state = FlowState.FAILED
        self._shot("failed")
        logger.error("流程失败 @%s: %s", self.state, message)
        return BookingResult(
            ok=False,
            state=self.state,
            message=message,
            campus=self._selected_campus,
            doctor=self._selected_doctor,
            artifacts=list(self._artifacts),
        )

    def run(self, *, warm_only: bool = False, poll_mode: bool = False) -> BookingResult:
        """执行预约。

        warm_only: 仅做到科室页热身（放号前）
        poll_mode: 已在医生/排班上下文，主要刷新抢可约
        """
        try:
            return self._run_inner(warm_only=warm_only, poll_mode=poll_mode)
        except Exception as exc:  # noqa: BLE001
            return self._fail(str(exc))

    def _run_inner(self, *, warm_only: bool, poll_mode: bool) -> BookingResult:
        if not poll_mode:
            self.state = FlowState.AUTH_READY
            self.session.ensure_authenticated()
            self._shot("auth_ready")

            self.state = FlowState.HOME
            self.adapter.open_outpatient_appointment()
            self._shot("home_to_appointment")

            self.state = FlowState.NOTICE
            self.adapter.accept_notice()
            self._shot("notice")

            # 院区 → 科室
            campus_ok = False
            for campus in self.policy.preferred_campus_order():
                self.state = FlowState.CAMPUS_SELECT
                if self.adapter.select_campus(campus):
                    self._selected_campus = campus
                    campus_ok = True
                    self._shot(f"campus_{campus}")
                    break
            if not campus_ok:
                return self._fail("未能按优先级选中任何院区")

            self.state = FlowState.DEPT_SELECT
            self.adapter.select_department()
            self._shot("department")

            if warm_only:
                return BookingResult(
                    ok=True,
                    state=self.state,
                    message="热身完成（已到科室页）",
                    campus=self._selected_campus,
                    artifacts=list(self._artifacts),
                )

        # 在优先级院区上找医生/可约
        self.state = FlowState.DOCTOR_DATE
        best = None
        for campus in self.policy.preferred_campus_order():
            # 若已在某院区，尝试切换
            self.adapter.select_campus(campus)
            self._selected_campus = campus
            candidates = self.adapter.list_doctor_candidates(campus)
            best = self.policy.pick_best(candidates)
            if best is not None:
                break
            # 若列表页本身就是医生卡片且含可约，直接尝试预约
            if self.adapter.has_available_slot_signal():
                break

        if best is not None:
            self._selected_doctor = best.doctor_name
            self.adapter.open_doctor(best.doctor_name)
            self.adapter.select_campus_tab_if_present(best.campus)
            self._selected_campus = best.campus
            self._shot("doctor")

        booked_date = self.adapter.select_available_date_and_book()
        if not booked_date:
            self.state = FlowState.NO_SLOT
            return BookingResult(
                ok=False,
                state=self.state,
                message="暂无可约日期",
                campus=self._selected_campus,
                doctor=self._selected_doctor,
                artifacts=list(self._artifacts),
            )

        self.state = FlowState.TIME_SLOT
        if not self.adapter.select_time_slot_and_confirm():
            return self._fail("时段选择或确认失败")
        self._shot("timeslot")

        self.state = FlowState.PATIENT_CONFIRM
        self.adapter.confirm_patient(self.config.booking.patient_name)
        self._shot("patient")

        if self.stop_before_captcha:
            return BookingResult(
                ok=True,
                state=self.state,
                message="已到验证码前（dry-run / stop_before_captcha）",
                campus=self._selected_campus,
                doctor=self._selected_doctor,
                artifacts=list(self._artifacts),
            )

        self.state = FlowState.CAPTCHA
        self.config.captcha_dir.mkdir(parents=True, exist_ok=True)
        captcha_shot = self.config.captcha_dir / f"captcha_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.adapter.screenshot(captcha_shot)
        self._artifacts.append(str(captcha_shot))
        code = self.captcha_provider(captcha_shot)
        if not code:
            return self._fail("验证码为空")

        self.adapter.fill_captcha_and_submit(
            code,
            confirm_submit=self.config.booking.confirm_submit,
            captcha_shot=captcha_shot,
        )
        self._shot("submitted")
        self.state = FlowState.SUBMITTED
        return BookingResult(
            ok=True,
            state=self.state,
            message="预约提交完成（请人工核验是否成功）",
            campus=self._selected_campus,
            doctor=self._selected_doctor,
            artifacts=list(self._artifacts),
        )

    def try_grab_once(self) -> BookingResult:
        """放号轮询中的单次尝试：刷新并抢可约。"""
        self.adapter.refresh_for_slots()
        return self.run(poll_mode=True)
