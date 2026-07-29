from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from robjy.adapters.shqmxx import selectors as sel
from robjy.config import AppConfig
from robjy.priority.policy import DoctorCandidate, PriorityPolicy, match_department

logger = logging.getLogger(__name__)


class ShqmxxAdapter:
    """上海九院齐脉 H5 页面操作适配。"""

    def __init__(self, page: Any, config: AppConfig, policy: PriorityPolicy) -> None:
        self.page = page
        self.config = config
        self.policy = policy
        self.timeout = config.booking.step_timeout_ms

    # ---------- helpers ----------

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path), full_page=True)

    def click_text(self, text: str, *, exact: bool = False, timeout: int | None = None) -> None:
        t = timeout if timeout is not None else self.timeout
        locator = self.page.get_by_text(text, exact=exact)
        locator.first.click(timeout=t)

    def click_button_like(self, text: str, timeout: int | None = None) -> None:
        t = timeout if timeout is not None else self.timeout
        # 优先 role=button，再退回文案
        btn = self.page.get_by_role("button", name=re.compile(re.escape(text)))
        if btn.count() > 0:
            btn.first.click(timeout=t)
            return
        self.click_text(text, exact=False, timeout=t)

    def wait_for_text(self, text: str, timeout: int | None = None) -> None:
        t = timeout if timeout is not None else self.timeout
        self.page.get_by_text(text, exact=False).first.wait_for(state="visible", timeout=t)

    def visible_texts(self) -> str:
        try:
            return self.page.inner_text("body")
        except Exception:  # noqa: BLE001
            return ""

    # ---------- flow steps ----------

    def open_outpatient_appointment(self) -> None:
        logger.info("进入门诊预约")
        self.click_text(sel.OUTPATIENT_APPOINTMENT, exact=True)
        # 可能直接到须知或院区列表
        self.page.wait_for_timeout(800)

    def accept_notice(self) -> None:
        body = self.visible_texts()
        if sel.NOTICE_YES in body or "预约须知" in body or "须知" in body:
            logger.info("确认预约须知：是")
            try:
                self.click_text(sel.NOTICE_YES, exact=True)
            except Exception:  # noqa: BLE001
                self.click_button_like(sel.NOTICE_YES)
            self.page.wait_for_timeout(500)

        body = self.visible_texts()
        if sel.NOTICE_GOT_IT in body:
            logger.info("确认：我知道了")
            try:
                self.click_text(sel.NOTICE_GOT_IT, exact=True)
            except Exception:  # noqa: BLE001
                self.click_button_like(sel.NOTICE_GOT_IT)
            self.page.wait_for_timeout(500)

    def select_campus(self, campus: str) -> bool:
        """在院区列表页或切换院区弹层中选择指定院区。成功返回 True。"""
        body = self.visible_texts()
        # 首页院区列表：名称通常为「上海第九人民医院南部院区」等
        target_patterns = [campus, f"上海第九人民医院{campus}"]
        for pattern in target_patterns:
            loc = self.page.get_by_text(pattern, exact=False)
            if loc.count() > 0:
                logger.info("选择院区: %s", pattern)
                loc.first.click(timeout=self.timeout)
                self.page.wait_for_timeout(800)
                return True

        # 已在科室页：尝试切换院区
        if sel.SWITCH_CAMPUS in body:
            logger.info("点击切换院区")
            self.click_text(sel.SWITCH_CAMPUS, exact=False)
            self.page.wait_for_timeout(500)
            loc = self.page.get_by_text(campus, exact=False)
            if loc.count() > 0:
                loc.first.click(timeout=self.timeout)
                self.page.wait_for_timeout(800)
                return True

        # 医生页顶部 tab
        tab = self.page.get_by_text(campus, exact=True)
        if tab.count() > 0:
            tab.first.click(timeout=self.timeout)
            self.page.wait_for_timeout(500)
            return True

        logger.warning("未能选择院区: %s", campus)
        return False

    def select_department(self) -> None:
        category = self.config.booking.department_category.strip()
        department = self.config.booking.department.strip()
        mode = self.config.booking.department_match

        if not department:
            raise ValueError("配置 booking.department 不能为空")

        if category:
            logger.info("选择科室大类: %s", category)
            cat = self.page.get_by_text(category, exact=False)
            if cat.count() == 0:
                raise LookupError(f"未找到科室大类: {category}")
            cat.first.click(timeout=self.timeout)
            self.page.wait_for_timeout(500)

        # 收集右侧可见科室文案
        body = self.visible_texts()
        # 粗粒度：按行拆分后做匹配
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        matched = match_department(lines, department, mode=mode)
        logger.info("选择科室: %s (matched=%s)", department, matched)
        self.page.get_by_text(matched, exact=False).first.click(timeout=self.timeout)
        self.page.wait_for_timeout(800)

    def list_doctor_candidates(self, campus: str) -> list[DoctorCandidate]:
        """从当前医生/排班列表解析候选。解析失败时返回空列表。"""
        body = self.visible_texts()
        candidates: list[DoctorCandidate] = []

        # 启发式：寻找「可约」附近的日期与职称
        # 实际 DOM 差异大，适配层尽量宽松；策略层做最终筛选
        title_pat = re.compile(r"(主任医师|副主任医师|主治医师|住院医师)")
        date_pat = re.compile(r"(20\d{2}-\d{2}-\d{2})")
        name_title_pat = re.compile(
            r"([\u4e00-\u9fff]{2,4})\s*(主任医师|副主任医师|主治医师|住院医师)"
        )

        for m in name_title_pat.finditer(body):
            name, title = m.group(1), m.group(2)
            # 取正文中第一个可约日期作为近似
            dates = date_pat.findall(body)
            avail = None
            if "可约" in body and dates:
                try:
                    avail = datetime.strptime(dates[0], "%Y-%m-%d").date()
                except ValueError:
                    avail = date.today()
            if avail is None:
                # 若页面展示「可约」卡片而无完整日期，先用占位，后续点进医生页再校正
                if sel.AVAILABLE not in body:
                    continue
                avail = date.today()

            candidates.append(
                DoctorCandidate(
                    doctor_name=name,
                    title=title,
                    campus=campus,
                    available_date=avail,
                    earliest_slot=None,
                    raw_label=m.group(0),
                )
            )

        # 去重
        uniq: dict[tuple, DoctorCandidate] = {}
        for c in candidates:
            key = (c.doctor_name, c.title, c.campus, c.available_date)
            uniq[key] = c
        result = list(uniq.values())
        logger.info("解析到候选医生 %d 人 (campus=%s)", len(result), campus)
        return result

    def open_doctor(self, doctor_name: str) -> None:
        logger.info("打开医生: %s", doctor_name)
        self.page.get_by_text(doctor_name, exact=False).first.click(timeout=self.timeout)
        self.page.wait_for_timeout(800)

    def select_campus_tab_if_present(self, campus: str) -> None:
        tab = self.page.get_by_text(campus, exact=True)
        if tab.count() > 0:
            logger.info("切换医生页院区 tab: %s", campus)
            tab.first.click(timeout=self.timeout)
            self.page.wait_for_timeout(400)

    def select_available_date_and_book(self) -> bool:
        """选择带「可约」的日期卡片，并点击对应「预约」。"""
        # 优先点击含「可约」的元素
        available = self.page.get_by_text(sel.AVAILABLE, exact=True)
        if available.count() == 0:
            logger.info("当前无「可约」日期")
            return False

        logger.info("选择可约日期")
        available.first.click(timeout=self.timeout)
        self.page.wait_for_timeout(400)

        book_btns = self.page.get_by_text(sel.BOOK, exact=True)
        if book_btns.count() == 0:
            logger.warning("未找到预约按钮")
            return False
        book_btns.first.click(timeout=self.timeout)
        self.page.wait_for_timeout(600)
        return True

    def select_time_slot_and_confirm(self, preferred_slot: str | None = None) -> bool:
        """在时段弹层中选时段并点确认。"""
        body = self.visible_texts()
        slot_pat = re.compile(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}")
        slots = slot_pat.findall(body)
        if not slots:
            # 有些弹层确认前先点时段
            logger.warning("未解析到时段按钮")
        else:
            chosen = preferred_slot
            if chosen is None:
                # 选第一个可点的白底时段：按文案依次尝试
                for s in slots:
                    compact = s.replace(" ", "")
                    loc = self.page.get_by_text(compact, exact=False)
                    if loc.count() == 0:
                        loc = self.page.get_by_text(s, exact=False)
                    if loc.count() > 0:
                        chosen = compact
                        break
            if chosen:
                logger.info("选择时段: %s", chosen)
                self.page.get_by_text(chosen, exact=False).first.click(timeout=self.timeout)
                self.page.wait_for_timeout(300)

        # 友情提示确认
        if "友情提示" in self.visible_texts() or sel.CONFIRM in self.visible_texts():
            logger.info("点击确认")
            try:
                self.click_text(sel.CONFIRM, exact=True)
            except Exception:  # noqa: BLE001
                self.click_button_like(sel.CONFIRM)
            self.page.wait_for_timeout(600)
            return True

        # 若点时段后直接弹出确认框
        confirm = self.page.get_by_text(sel.CONFIRM, exact=True)
        if confirm.count() > 0:
            confirm.first.click(timeout=self.timeout)
            self.page.wait_for_timeout(600)
            return True

        return bool(slots)

    def confirm_patient(self, patient_name: str) -> None:
        body = self.visible_texts()
        if patient_name:
            if patient_name not in body:
                # 尝试点击姓名选择
                loc = self.page.get_by_text(patient_name, exact=False)
                if loc.count() > 0:
                    logger.info("选择就诊人: %s", patient_name)
                    loc.first.click(timeout=self.timeout)
                    self.page.wait_for_timeout(400)
                else:
                    logger.warning("页面未直接展示就诊人 %s，继续尝试确认", patient_name)
            else:
                logger.info("就诊人已在页: %s", patient_name)

        # 常见确认按钮
        for label in ("确认", "确定", "下一步", "预约"):
            loc = self.page.get_by_text(label, exact=True)
            if loc.count() > 0 and label != "预约":
                # 就诊人页的确认，避免过早点最终预约
                logger.info("就诊人步骤点击: %s", label)
                loc.first.click(timeout=self.timeout)
                self.page.wait_for_timeout(500)
                break

    def fill_captcha_and_submit(
        self,
        captcha_code: str,
        *,
        confirm_submit: bool,
        captcha_shot: Path | None = None,
    ) -> None:
        if captcha_shot is not None:
            self.screenshot(captcha_shot)

        # 常见验证码输入框
        input_candidates = [
            self.page.locator("input[type='text']"),
            self.page.locator("input[type='tel']"),
            self.page.locator("input[placeholder*='验证']"),
            self.page.locator("input[placeholder*='校验']"),
        ]
        filled = False
        for loc in input_candidates:
            if loc.count() > 0:
                loc.last.fill(captcha_code)
                filled = True
                break
        if not filled:
            # 退回：最后一个可见 input
            inputs = self.page.locator("input")
            if inputs.count() > 0:
                inputs.last.fill(captcha_code)
                filled = True
        if not filled:
            raise RuntimeError("未找到验证码输入框")

        if confirm_submit:
            answer = input("即将提交预约，确认继续？[y/N]: ").strip().lower()
            if answer not in {"y", "yes", "是"}:
                raise RuntimeError("用户取消最终提交")

        logger.info("提交预约")
        self.click_text(sel.BOOK, exact=True)

    def refresh_for_slots(self) -> None:
        """轻量刷新以发现新号源。"""
        try:
            self.page.reload(wait_until="domcontentloaded")
        except Exception:  # noqa: BLE001
            logger.debug("reload 失败，尝试再次 goto 当前 URL", exc_info=True)
            self.page.goto(self.page.url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(300)

    def has_available_slot_signal(self) -> bool:
        body = self.visible_texts()
        return sel.AVAILABLE in body or bool(re.search(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}", body))
