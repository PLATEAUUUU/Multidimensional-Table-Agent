"""
面试官多维表记录定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class InterviewerRecord:
    """面试官基础信息记录。"""

    record_id: str | None
    interviewer_id: str
    name: str
    rounds: list[str] = field(default_factory=list)

