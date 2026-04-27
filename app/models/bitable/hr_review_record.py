"""
HR 初筛评审多维表记录定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HRReviewRecord:
    """HR 初筛评审记录。"""

    record_id: str | None
    candidate_id: str
    screening_passed: bool
    score: float
    reason: str
    reviewer: str
    review_time: str

