"""
HR 谈薪与录用多维表记录定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HRCompRecord:
    """HR 谈薪或录用阶段记录。"""

    record_id: str | None
    candidate_id: str
    compensation: str
    offer_status: str
    hr_reviewer: str
    note: str
    updated_time: str

