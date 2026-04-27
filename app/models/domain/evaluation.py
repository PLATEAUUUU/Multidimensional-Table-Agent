"""
评估结果领域模型定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Evaluation(BaseModel):
    """轮次评估实体。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    # 内部持久化主键，用于与外部记录表建立映射。
    id: str | None = Field(default=None, description="内部主键。")
    evaluation_id: str = Field(..., description="评估业务 ID。")
    candidate_id: str = Field(..., description="候选人 ID。")
    round_id: str = Field(..., description="所属面试轮次 ID。")
    score: float | None = Field(default=None, description="评估分数。")
    summary: str = Field(..., description="评估摘要。")
    detailed_comment: str = Field(..., description="详细评语。")
    created_at: str = Field(..., description="评估创建时间，ISO 8601 字符串。")

