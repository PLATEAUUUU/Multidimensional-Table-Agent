"""
流程状态响应 DTO 定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ...enums import CandidateProcessStatus, InterviewRoundStatus


class InterviewRoundDTO(BaseModel):
    """流程页面中的单轮面试展示模型。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    round_id: str = Field(..., description="轮次 ID。")
    round_name: str = Field(..., description="轮次名称。")
    status: InterviewRoundStatus = Field(..., description="轮次状态。")
    enterable: bool = Field(..., description="当前轮次是否允许进入。")


class ProcessStateDTO(BaseModel):
    """候选人整体流程状态响应模型。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    candidate_id: str = Field(..., description="候选人 ID。")
    candidate_name: str = Field(..., description="候选人姓名。")
    process_status: CandidateProcessStatus = Field(..., description="候选人整体流程状态。")
    current_round: str | None = Field(default=None, description="当前轮次 ID。")
    process_finished: bool = Field(..., description="整体流程是否结束。")
    rounds: list[InterviewRoundDTO] = Field(default_factory=list, description="各轮次状态列表。")

