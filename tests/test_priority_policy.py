from __future__ import annotations

from datetime import date, time

import pytest

from robjy.priority.policy import (
    DepartmentNotFoundError,
    DoctorCandidate,
    PriorityPolicy,
    match_department,
)


def _c(
    name: str,
    title: str,
    campus: str,
    day: date,
    slot: time | None = None,
) -> DoctorCandidate:
    return DoctorCandidate(
        doctor_name=name,
        title=title,
        campus=campus,
        available_date=day,
        earliest_slot=slot,
    )


def test_match_department_exact():
    assert match_department(["儿童口腔科", "口腔外科"], "儿童口腔科", mode="exact") == "儿童口腔科"


def test_match_department_contains_prefers_shortest():
    got = match_department(
        ["口腔科", "儿童口腔科", "口腔颌面外科"],
        "口腔",
        mode="contains",
    )
    assert got == "口腔科"


def test_match_department_not_found():
    with pytest.raises(DepartmentNotFoundError):
        match_department(["骨科"], "儿童口腔科", mode="contains")


def test_prefer_southern_over_gaoke():
    policy = PriorityPolicy()
    best = policy.pick_best(
        [
            _c("甲", "主任医师", "高科园区", date(2026, 8, 11), time(13, 30)),
            _c("乙", "主任医师", "南部院区", date(2026, 8, 12), time(9, 0)),
        ]
    )
    assert best is not None
    assert best.campus == "南部院区"
    assert best.doctor_name == "乙"


def test_fallback_gaoke_when_south_missing():
    policy = PriorityPolicy()
    best = policy.pick_best(
        [
            _c("甲", "主任医师", "高科园区", date(2026, 8, 11)),
            _c("丙", "主任医师", "北部院区", date(2026, 8, 10)),
        ]
    )
    assert best is not None
    assert best.campus == "高科园区"


def test_prefer_chief_over_associate():
    policy = PriorityPolicy()
    best = policy.pick_best(
        [
            _c("汪隼", "副主任医师", "南部院区", date(2026, 8, 11), time(14, 30)),
            _c("某主任", "主任医师", "南部院区", date(2026, 8, 12), time(9, 0)),
        ]
    )
    assert best is not None
    assert best.title == "主任医师"


def test_tie_break_earliest_date_then_slot():
    policy = PriorityPolicy()
    best = policy.pick_best(
        [
            _c("A", "主任医师", "南部院区", date(2026, 8, 12), time(9, 0)),
            _c("B", "主任医师", "南部院区", date(2026, 8, 11), time(15, 0)),
            _c("C", "主任医师", "南部院区", date(2026, 8, 11), time(14, 30)),
        ]
    )
    assert best is not None
    assert best.doctor_name == "C"
    assert best.available_date == date(2026, 8, 11)
    assert best.earliest_slot == time(14, 30)


def test_skip_unlisted_title_by_default():
    policy = PriorityPolicy()
    best = policy.pick_best(
        [
            _c("丁", "主治医师", "南部院区", date(2026, 8, 11)),
        ]
    )
    assert best is None


def test_parse_slot_start():
    assert PriorityPolicy.parse_slot_start("14:30-15:00") == time(14, 30)
    assert PriorityPolicy.parse_slot_start("9:00") == time(9, 0)
