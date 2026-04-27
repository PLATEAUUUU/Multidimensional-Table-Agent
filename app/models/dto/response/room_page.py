"""
流程状态响应 DTO 定义。

创建时间: 2026-04-27
开发人: zcry
"""

# app/schemas/response/interview_page.py

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    CandidateProcessStatus,
    InterviewRoundStatus,
    InterviewRoundType,
)


class InterviewerBriefDTO(BaseModel):
    """面试官简要展示信息"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    interviewer_id: str = Field(..., description="面试官 ID")
    name: str = Field(..., description="面试官姓名")
    title: str | None = Field(default=None, description="面试官职位，如高级后端工程师")


class InterviewRoomDTO(BaseModel):
    """左侧单个面试聊天室展示模型"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    round_type: InterviewRoundType = Field(..., description="面试轮次")
    round_name: str = Field(..., description="面试轮次展示名称")
    status: InterviewRoundStatus = Field(..., description="聊天室/轮次状态")
    status_text: str = Field(..., description="状态展示文案")
    enterable: bool = Field(..., description="是否允许进入")
    interviewer: InterviewerBriefDTO | None = Field(default=None, description="该轮面试官信息")


class InterviewPageStateDTO(BaseModel):
    """面试页面初始化状态"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    candidate_id: str = Field(..., description="候选人 ID")
    candidate_name: str = Field(..., description="候选人姓名")

    process_status: CandidateProcessStatus = Field(..., description="候选人整体流程状态")
    process_finished: bool = Field(..., description="流程是否结束")

    current_round: InterviewRoundType | None = Field(default=None, description="当前面试轮次")

    rooms: list[InterviewRoomDTO] = Field(
        default_factory=list,
        description="左侧面试聊天室列表",
    )