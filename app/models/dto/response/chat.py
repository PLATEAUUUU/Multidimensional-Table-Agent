"""
聊天与轮次推进响应 DTO 定义

创建时间: 2026-04-27
开发人: zcry
"""

# app/schemas/response/chat.py

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InterviewRoundStatus, InterviewRoundType


class ChatSessionDTO(BaseModel):
    """进入聊天室后的响应模型"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    candidate_id: str = Field(..., description="候选人 ID")
    round_type: InterviewRoundType = Field(..., description="当前面试轮次")
    round_name: str = Field(..., description="当前面试轮次名称")
    status: InterviewRoundStatus = Field(..., description="当前轮次状态")


class ChatMessageDTO(BaseModel):
    """聊天消息响应模型"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    message_id: str = Field(..., description="消息 ID")
    role: Literal["AGENT", "CANDIDATE"] = Field(..., description="消息发送角色")
    content: str = Field(..., description="消息文本内容")
    created_at: str = Field(..., description="消息创建时间，ISO 8601 字符串")


class NextRoundInfoDTO(BaseModel):
    """下一轮信息响应模型"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    round_type: InterviewRoundType = Field(..., description="下一轮轮次")
    round_name: str = Field(..., description="下一轮轮次名称")
    unlocked: bool = Field(..., description="下一轮是否已解锁")


class InterviewTurnResultDTO(BaseModel):
    """单次对话推进后的结果模型"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    agent_message: ChatMessageDTO | None = Field(
        default=None,
        description="Agent 回复消息,为空表示本次只有状态变化，没有新增 Agent 发言",
    )

    round_status: InterviewRoundStatus = Field(..., description="当前轮次最新状态")
    round_finished: bool = Field(..., description="当前轮次是否结束")
    round_passed: bool | None = Field(default=None, description="当前轮次是否通过")

    process_finished: bool = Field(..., description="整体流程是否结束")
    next_round: NextRoundInfoDTO | None = Field(default=None, description="下一轮解锁信息")

