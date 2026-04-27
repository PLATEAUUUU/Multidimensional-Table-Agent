"""
候选人领域模型定义

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from ..enums import CandidateProcessStatus, InterviewRoundType


class Candidate(BaseModel):
    """候选人领域实体"""

    id: str | None = Field(default=None, description="内部主键")
    candidate_id: str = Field(..., description="候选人业务唯一标识")
    candidate_name: str = Field(..., description="候选人姓名")
    target_position: str | None = Field(default=None, description="候选人目标岗位")

    resume_id: str | None = Field(default=None, description="关联简历 ID")

    screening_passed: bool | None = Field(default=None, description="HR 初筛是否通过")
    process_status: CandidateProcessStatus = Field(..., description="候选人整体流程状态")
    current_round: InterviewRoundType | None = Field(default=None, description="当前所处面试轮次")