# app/models/domain/agent_run.py
"""
SubAgent 运行时记录

职责：
1. 表达一次 agent 执行的完整运行记录
2. 记录输入、输出、工具调用、耗时和错误信息
3. 为 observer / 审计 / 调试 / 持久化提供统一结构

创建时间：2026/4/28
开发人：zcry
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.tools.result import ToolCallRecord


AgentRunStatus = Literal[
    "started",
    "success",
    "failed",
    "blocked",
    "timeout",
]


class AgentRunRecord(BaseModel):
    """Agent / SubGraph 运行记录"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    trace_id: str = Field(..., description="链路追踪 ID")
    run_id: str = Field(..., description="本次 Agent 执行 ID")

    agent_name: str = Field(..., description="当前 Agent 名称")
    model_name: str | None = Field(default=None, description="本次使用的模型名称")

    candidate_id: str | None = Field(default=None, description="候选人 ID")
    round_type: str | None = Field(default=None, description="面试轮次")
    process_status: str | None = Field(default=None, description="流程状态快照")

    status: AgentRunStatus = Field(..., description="本次运行状态")

    input_snapshot: dict[str, Any] = Field(default_factory=dict, description="输入快照")
    output_snapshot: dict[str, Any] = Field(default_factory=dict, description="输出快照")

    tool_calls: list[ToolCallRecord] = Field(default_factory=list, description="工具调用记录")

    summary: str | None = Field(default=None, description="本次运行摘要")

    error_code: str | None = Field(default=None, description="错误码")
    error_message: str | None = Field(default=None, description="错误消息")

    started_at: datetime = Field(..., description="开始时间")
    finished_at: datetime | None = Field(default=None, description="结束时间")
    duration_ms: int | None = Field(default=None, ge=0, description="耗时（毫秒）")