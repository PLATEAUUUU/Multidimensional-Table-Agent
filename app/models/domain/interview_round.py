"""
面试轮次领域模型定义

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..enums import InterviewRoundStatus, InterviewRoundType


class InterviewRound(BaseModel):
    """候选人面试轮次实体"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    # 内部持久化主键，用于和业务 round_id 区分
    id: str | None = Field(default=None, description="内部主键")
    round_id: str = Field(..., description="轮次业务 ID")
    candidate_id: str = Field(..., description="候选人 ID")

    round_type: InterviewRoundType = Field(..., description="轮次类型")
    status: InterviewRoundStatus = Field(..., description="轮次状态")

    start_time: str | None = Field(default=None, description="轮次开始时间，ISO 8601 字符串")
    end_time: str | None = Field(default=None, description="轮次结束时间，ISO 8601 字符串")

