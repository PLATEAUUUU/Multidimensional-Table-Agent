"""
Agent 输出基类

创建时间：2026/4/28
开发人：zcry
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import InterviewRoundType


class BaseAgentOutput(BaseModel):
    """所有 Agent 节点输出的基类"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    output_type: str = Field(..., description="输出类型，用于区分具体 Agent 输出")
    agent_name: str = Field(..., description="产生该输出的 Agent 名称")
    candidate_id: str = Field(..., description="候选人 ID")

    round_type: InterviewRoundType | None = Field(
        default=None,
        description="关联的面试轮次；简历解析等非轮次节点可为空",
    )

    decision: Literal["pass", "reject", "continue", "parsed"] | None = Field(
        default=None,
        description="节点决策结果",
    )

    summary: str | None = Field(default=None, description="节点输出摘要")