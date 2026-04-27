"""
聊天会话领域模型定义

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from ..enums import InterviewRoundStatus, InterviewRoundType


class ChatSession(BaseModel):
    """面试轮次聊天会话实体"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    # 内部持久化主键，和业务 session_id 可以分离
    id: str | None = Field(default=None, description="内部主键")
    session_id: str = Field(..., description="聊天会话业务 ID")
    candidate_id: str = Field(..., description="候选人 ID")
    round_type: InterviewRoundType = Field(..., description="所属面试轮次")
    status: InterviewRoundStatus = Field(..., description="聊天会话状态")
