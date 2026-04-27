"""
候选人多维表记录定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CandidateRecord:
    """候选人基础信息表记录。"""

    # record_id 对应飞书多维表的行记录主键。
    record_id: str | None
    candidate_id: str
    name: str
    position: str
    process_status: str
    created_time: str

