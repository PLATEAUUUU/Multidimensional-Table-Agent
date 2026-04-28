"""
Agent 轮次输出 DTO 定义

创建时间: 2026-04-28
开发人: zcry
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from app.models.domain.candidate import Candidate
from app.models.domain.resume import Resume
from app.models.domain.evaluation import Evaluation
from app.models.domain.interview_round import InterviewRound
from app.models.domain.interviewer import Interviewer
from app.models.domain.chat_message import ChatMessage

class ResumeParseOutput(BaseModel):
    """简历解析节点输出"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    candidate: Candidate = Field(..., description="解析得到的候选人实体")
    resume: Resume = Field(..., description="解析得到的简历实体")


class HRScreeningOutput(BaseModel):
    """HR 初筛节点输出"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    decision: Literal["pass", "reject"] = Field(..., description="初筛结论")
    evaluation: Evaluation = Field(..., description="HR 初筛评价")
    updated_round: InterviewRound = Field(..., description="更新后的 HR 初筛轮次")

    next_round: InterviewRound | None = Field(default=None, description="下一轮面试")
    next_interviewer: Interviewer | None = Field(default=None, description="下一轮面试官")


class InterviewRoundOutput(BaseModel):
    """面试轮次 Agent 输出"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    decision: Literal["pass", "reject", "continue"] = Field(..., description="本次 Agent 决策")

    agent_message: ChatMessage | None = Field(
        default=None,
        description="Agent 本次生成的问题或回复",
    )

    evaluation: Evaluation | None = Field(
        default=None,
        description="如果本轮结束，则生成面评",
    )

    updated_round: InterviewRound = Field(..., description="更新后的当前轮次")

    next_round: InterviewRound | None = Field(default=None, description="下一轮面试")
    next_interviewer: Interviewer | None = Field(default=None, description="下一轮面试官")