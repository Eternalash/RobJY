from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from robjy.config import AppConfig
from robjy.flow.booking import BookingFlow, BookingResult, FlowState
from robjy.session.browser import BrowserSession

logger = logging.getLogger(__name__)


@dataclass
class ScheduleOutcome:
    result: BookingResult
    attempts: int
    started_at: datetime
    finished_at: datetime
    reason: str


class ReleaseScheduler:
    """07:30 放号窗口调度：热身 → 轮询抢号。"""

    def __init__(self, config: AppConfig, session: BrowserSession) -> None:
        self.config = config
        self.session = session
        self.tz = ZoneInfo(config.scheduler.timezone)

    def _now(self) -> datetime:
        return datetime.now(self.tz)

    def _today_release_at(self) -> datetime:
        hh, mm, ss = [int(x) for x in self.config.scheduler.release_time.split(":")]
        now = self._now()
        return now.replace(hour=hh, minute=mm, second=ss, microsecond=0)

    def wait_until(self, target: datetime, label: str) -> None:
        while True:
            now = self._now()
            remain = (target - now).total_seconds()
            if remain <= 0:
                return
            sleep_for = min(remain, 1.0)
            if int(remain) % 10 == 0 or remain < 5:
                logger.info("等待 %s，剩余 %.1fs", label, remain)
            time.sleep(sleep_for)

    def run_scheduled(
        self,
        *,
        captcha_provider=None,
        stop_before_captcha: bool = False,
    ) -> ScheduleOutcome:
        release_at = self._today_release_at()
        now = self._now()
        if now > release_at + timedelta(seconds=self.config.scheduler.poll_window_sec):
            # 今日窗口已过，转到次日
            release_at = release_at + timedelta(days=1)
            logger.info("今日放号窗口已过，调度到次日 %s", release_at.isoformat())

        warmup_at = release_at - timedelta(seconds=self.config.scheduler.warmup_lead_sec)
        self.wait_until(warmup_at, "热身开始")

        flow = BookingFlow(
            self.config,
            self.session,
            captcha_provider=captcha_provider,
            stop_before_captcha=stop_before_captcha,
        )

        logger.info("开始热身导航")
        warm = flow.run(warm_only=True)
        if not warm.ok:
            finished = self._now()
            return ScheduleOutcome(
                result=warm,
                attempts=0,
                started_at=now,
                finished_at=finished,
                reason="warmup_failed",
            )

        self.wait_until(release_at, "放号")

        window_end = release_at + timedelta(seconds=self.config.scheduler.poll_window_sec)
        interval = max(0.05, float(self.config.scheduler.poll_interval_sec))
        max_attempts = self.config.scheduler.max_attempts
        attempts = 0
        last: BookingResult = BookingResult(
            ok=False, state=FlowState.NO_SLOT, message="尚未开始轮询"
        )

        logger.info(
            "进入轮询: window_end=%s interval=%.3fs max_attempts=%d",
            window_end.isoformat(),
            interval,
            max_attempts,
        )

        while attempts < max_attempts and self._now() <= window_end:
            attempts += 1
            t0 = time.monotonic()
            last = flow.try_grab_once()
            if last.ok and last.state in {FlowState.SUBMITTED, FlowState.PATIENT_CONFIRM}:
                # PATIENT_CONFIRM 仅在 stop_before_captcha 时算阶段性成功
                if last.state == FlowState.SUBMITTED or stop_before_captcha:
                    finished = self._now()
                    logger.info(
                        "抢号成功 attempts=%d state=%s msg=%s",
                        attempts,
                        last.state,
                        last.message,
                    )
                    return ScheduleOutcome(
                        result=last,
                        attempts=attempts,
                        started_at=now,
                        finished_at=finished,
                        reason="success",
                    )
            if last.state == FlowState.FAILED and "用户取消" in last.message:
                finished = self._now()
                return ScheduleOutcome(
                    result=last,
                    attempts=attempts,
                    started_at=now,
                    finished_at=finished,
                    reason="cancelled",
                )

            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, interval - elapsed))

        finished = self._now()
        reason = "timeout" if self._now() > window_end or attempts >= max_attempts else "stopped"
        if last.state != FlowState.FAILED:
            last = BookingResult(
                ok=False,
                state=FlowState.NO_SLOT,
                message=f"放号窗口结束仍未抢到（attempts={attempts}）",
                campus=last.campus,
                doctor=last.doctor,
                artifacts=last.artifacts,
            )
        logger.warning("抢号结束 reason=%s attempts=%d last=%s", reason, attempts, last.message)
        return ScheduleOutcome(
            result=last,
            attempts=attempts,
            started_at=now,
            finished_at=finished,
            reason=reason,
        )

    @staticmethod
    def summarize(outcome: ScheduleOutcome) -> str:
        return (
            f"reason={outcome.reason} attempts={outcome.attempts} "
            f"ok={outcome.result.ok} state={outcome.result.state.value} "
            f"msg={outcome.result.message} "
            f"campus={outcome.result.campus} doctor={outcome.result.doctor} "
            f"elapsed={(outcome.finished_at - outcome.started_at).total_seconds():.1f}s"
        )
