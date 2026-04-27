"""
面试官领域模型定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Interviewer(BaseModel):
    """面试官实体。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    # 内部持久化主键，用于兼容本地库或外部系统映射。
    id: str | None = Field(default=None, description="内部主键。")
    interviewer_id: str = Field(..., description="面试官业务 ID。")
    name: str = Field(..., description="面试官名称。")
    role: str = Field(..., description="面试官角色，例如 technical_1 或 manager。")
    agent_config: dict[str, Any] | None = Field(
        default=None,
        description="面试 Agent 配置快照。",
    )

