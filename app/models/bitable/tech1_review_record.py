"""
技术一面评审多维表记录定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Tech1ReviewRecord:
    """技术一面评审记录。"""

    record_id: str | None
    candidate_id: str
    score: float
    summary: str
    detail: str
    interviewer: str
    review_time: str

