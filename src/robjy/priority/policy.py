from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Iterable, Sequence


class DepartmentNotFoundError(LookupError):
    """配置科室在候选列表中未匹配到。"""


@dataclass(frozen=True, slots=True)
class DoctorCandidate:
    """可约候选（适配层解析后的统一结构）。"""

    doctor_name: str
    title: str
    campus: str
    available_date: date
    earliest_slot: time | None = None
    raw_label: str = ""


def match_department(
    candidates: Sequence[str],
    target: str,
    mode: str = "contains",
) -> str:
    """在科室名列表中匹配目标科室。

    mode:
      - exact: 去除空白后全等
      - contains: 目标被候选包含，或候选被目标包含；多命中取最短候选
    """
    if not target or not target.strip():
        raise ValueError("目标科室名不能为空")

    needle = target.strip()
    normalized = [(c, c.strip()) for c in candidates if c and c.strip()]

    if mode == "exact":
        hits = [orig for orig, text in normalized if text == needle]
    elif mode == "contains":
        hits = [
            orig
            for orig, text in normalized
            if needle in text or text in needle
        ]
    else:
        raise ValueError(f"不支持的 department_match: {mode}")

    if not hits:
        raise DepartmentNotFoundError(f"未找到科室: {needle!r}（mode={mode}）")

    # 多命中时取最短名称，降低误选大类概率
    hits.sort(key=lambda s: (len(s.strip()), s.strip()))
    return hits[0]


class PriorityPolicy:
    """院区 / 职称优先级与确定性 tie-break。"""

    def __init__(
        self,
        campus_priority: Sequence[str] | None = None,
        title_priority: Sequence[str] | None = None,
        allow_unlisted_campus: bool = False,
        allow_unlisted_title: bool = False,
    ) -> None:
        self.campus_priority = list(campus_priority or ["南部院区", "高科园区"])
        self.title_priority = list(title_priority or ["主任医师", "副主任医师"])
        self.allow_unlisted_campus = allow_unlisted_campus
        self.allow_unlisted_title = allow_unlisted_title

    def campus_rank(self, campus: str) -> int | None:
        text = campus.strip()
        for idx, name in enumerate(self.campus_priority):
            if text == name or name in text or text in name:
                return idx
        return None if not self.allow_unlisted_campus else len(self.campus_priority)

    @staticmethod
    def _title_matches(title: str, expected: str) -> bool:
        """职称匹配：先精确，再包含；避免「副主任医师」命中「主任医师」。"""
        t = title.strip()
        n = expected.strip()
        if not t or not n:
            return False
        if t == n:
            return True
        if n == "主任医师":
            return "主任医师" in t and "副主任医师" not in t
        if n == "副主任医师":
            return "副主任医师" in t
        return n in t or t in n

    def title_rank(self, title: str) -> int | None:
        for idx, name in enumerate(self.title_priority):
            if self._title_matches(title, name):
                return idx
        return None if not self.allow_unlisted_title else len(self.title_priority)

    def filter_candidates(self, candidates: Iterable[DoctorCandidate]) -> list[DoctorCandidate]:
        kept: list[DoctorCandidate] = []
        for c in candidates:
            if self.campus_rank(c.campus) is None:
                continue
            if self.title_rank(c.title) is None:
                continue
            kept.append(c)
        return kept

    def pick_best(self, candidates: Iterable[DoctorCandidate]) -> DoctorCandidate | None:
        """按院区 → 职称 → 最早日期 → 最早时段 → 医生名 排序取最优。"""
        filtered = self.filter_candidates(candidates)
        if not filtered:
            return None

        def sort_key(c: DoctorCandidate) -> tuple:
            campus_r = self.campus_rank(c.campus)
            title_r = self.title_rank(c.title)
            assert campus_r is not None and title_r is not None
            slot = c.earliest_slot or time.max
            return (
                campus_r,
                title_r,
                c.available_date,
                slot,
                c.doctor_name,
            )

        filtered.sort(key=sort_key)
        return filtered[0]

    def preferred_campus_order(self) -> list[str]:
        return list(self.campus_priority)

    @staticmethod
    def parse_date(value: str | date | datetime) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m.%d", "%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt)
                if fmt in ("%m.%d", "%m-%d"):
                    # 缺少年份时由调用方补全；此处用当年占位
                    return date(datetime.now().year, parsed.month, parsed.day)
                return parsed.date()
            except ValueError:
                continue
        raise ValueError(f"无法解析日期: {value!r}")

    @staticmethod
    def parse_slot_start(slot_text: str) -> time | None:
        """从 '14:30-15:00' 或 '14:30' 解析开始时刻。"""
        text = slot_text.strip()
        if not text:
            return None
        start = text.split("-", 1)[0].strip()
        try:
            return datetime.strptime(start, "%H:%M").time()
        except ValueError:
            return None
