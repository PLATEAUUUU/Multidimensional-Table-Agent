"""
面试官领域模型定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..enums import InterviewRoundType


class AgentConfig(BaseModel):
    """面试 Agent 个性化配置"""

    model_config = ConfigDict(extra="forbid")

    persona: str | None = Field(default=None, description="Agent 人设，例如严谨型技术面试官")
    interview_style: str | None = Field(default=None, description="面试风格，例如追问深入、偏项目经历")
    focus_areas: list[str] = Field(default_factory=list, description="重点考察方向")
    difficulty_level: str | None = Field(default=None, description="难度等级，例如 easy/medium/hard")
    question_count: int | None = Field(default=None, description="建议提问数量")
    scoring_rubric: dict[str, float] = Field(default_factory=dict, description="评分维度权重")
    system_prompt: str | None = Field(default=None, description="额外系统提示词")


class Interviewer(BaseModel):
    """面试官实体"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str | None = Field(default=None, description="内部主键")
    interviewer_id: str = Field(..., description="面试官业务 ID")
    name: str = Field(..., description="面试官名称")

    round_type: InterviewRoundType = Field(..., description="适用的面试轮次")

    agent_config: AgentConfig = Field(
        default_factory=AgentConfig,
        description="面试 Agent 个性化配置",
    )