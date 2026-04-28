# app/models/domain/agent_run.py
"""
SubAgent 运行时记录 DTO

创建时间：2026/4/28
开发人：zcry
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# TODO:更新内容
# AgentRunRecord 增加：
# agent_name
# status
# error_code
# error_message
# started_at
# finished_at
# duration_ms
# trace_id
# ToolCallRecord 增加：
# duration_ms
# trace_id
# run_id
# error_code


class ToolCallRecord(BaseModel):
    """工具调用记录"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    tool_name: str = Field(..., description="工具名称")
    arguments: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    result: dict[str, Any] | str | None = Field(default=None, description="工具返回结果")
    success: bool = Field(..., description="是否成功")
    error_message: str | None = Field(default=None, description="错误信息")
    created_at: str = Field(..., description="调用时间")


class AgentRunRecord(BaseModel):
    """Agent / SubGraph 运行记录"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    run_id: str = Field(..., description="运行 ID")
    candidate_id: str = Field(..., description="候选人 ID")
    subgraph_name: str = Field(..., description="子图名称")
    round_type: str | None = Field(default=None, description="面试轮次")

    input_snapshot: dict[str, Any] = Field(default_factory=dict, description="输入快照")
    output_snapshot: dict[str, Any] = Field(default_factory=dict, description="输出快照")

    tool_calls: list[ToolCallRecord] = Field(default_factory=list, description="工具调用记录")
    summary: str | None = Field(default=None, description="本次运行摘要")
    created_at: str = Field(..., description="创建时间")