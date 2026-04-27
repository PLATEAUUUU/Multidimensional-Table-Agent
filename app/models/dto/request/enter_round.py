"""
进入轮次请求 DTO 定义

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EnterRoundRequest(BaseModel):
    """进入某一轮面试的空请求体"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

