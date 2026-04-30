"""
Tool 工具调用结果，定义工具调用上下文，返回结构化的ToolResult

创建时间：2026/4/29
开发人：zcry
"""
from __future__ import annotations

from typing import Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.core.tools.errors import ToolError


class ToolCallContext(BaseModel):
    """
    一次工具调用的基础上下文

    说明：
    - runtime.py 在执行工具前应先构造这个对象
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    trace_id: str = Field(..., description="链路追踪 ID")
    run_id: str = Field(..., description="当前 Agent 执行 ID")
    tool_name: str = Field(..., description="工具名称")
    agent_name: str | None = Field(default=None, description="调用该工具的 Agent 名称")


class ToolCallRecord(BaseModel):
    """
    一次工具调用的完整记录
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    context: ToolCallContext = Field(..., description="工具调用上下文")
    arguments: dict[str, Any] = Field(default_factory=dict, description="调用参数")

    started_at: datetime = Field(..., description="开始时间")
    finished_at: datetime | None = Field(default=None, description="结束时间")
    duration_ms: int | None = Field(default=None, ge=0, description="耗时（毫秒）")

    result: ToolResult | None = Field(default=None, description="执行结果")

    @property
    def success(self) -> bool | None:
        """便捷属性：如果结果存在，返回成功状态"""
        if self.result is None:
            return None
        return self.result.success


class ToolErrorPayload(BaseModel):
    """
    工具失败时的结构化错误载荷

    说明：
    - ToolError 是运行时内部异常
    - ToolErrorPayload 是给 ToolResult.error 用的可序列化结构
    - suggest 由 runtime.py 注入，不由 errors.py 负责
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    error_type: str = Field(..., description="错误类型名")
    error_code: str = Field(..., description="错误码")
    error_message: str = Field(..., description="错误消息")
    details: dict[str, Any] = Field(default_factory=dict, description="结构化错误细节")
    suggest: list[str] = Field(default_factory=list, description="建议动作")



class ToolResult(BaseModel):
    """
    工具统一结果结构

    约定：
    - success=True 时，error 必须为空
    - success=False 时，error 必须存在
    - data 只表示工具执行产物
    - metadata 只放附加信息，不放核心调用参数
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    tool_name: str = Field(..., description="工具名称")
    success: bool = Field(..., description="是否执行成功")

    trace_id: str = Field(..., description="链路追踪 ID")
    run_id: str = Field(..., description="当前 Agent 执行 ID")
    agent_name: str | None = Field(default=None, description="调用工具的 Agent 名称")

    duration_ms: int = Field(default=0, ge=0, description="工具耗时（毫秒）")

    data: Any | None = Field(default=None, description="成功时的工具返回数据")
    error: ToolErrorPayload | None = Field(default=None, description="失败时的错误载荷")

    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元信息")

    @model_validator(mode="after")
    def validate_success_error_consistency(self) -> "ToolResult":
        """保证 success / error 的组合合法"""
        if self.success and self.error is not None:
            raise ValueError("ToolResult.success=True 时不能同时存在 error")

        if not self.success and self.error is None:
            raise ValueError("ToolResult.success=False 时必须提供 error")

        return self

    @classmethod
    def ok(
        cls,
        *,
        context: ToolCallContext,
        data: Any = None,
        duration_ms: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResult":
        """构造成功结果"""
        return cls(
            tool_name=context.tool_name,
            success=True,
            trace_id=context.trace_id,
            run_id=context.run_id,
            agent_name=context.agent_name,
            duration_ms=duration_ms,
            data=data,
            error=None,
            metadata=metadata or {},
        )

    @classmethod
    def fail(
        cls,
        *,
        context: ToolCallContext,
        error: ToolError,
        duration_ms: int = 0,
        suggest: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResult":
        """构造失败结果"""
        payload = error.to_dict()

        return cls(
            tool_name=context.tool_name,
            success=False,
            trace_id=context.trace_id,
            run_id=context.run_id,
            agent_name=context.agent_name,
            duration_ms=duration_ms,
            data=None,
            error=ToolErrorPayload(
                error_type=str(payload["error_type"]),
                error_code=str(payload["error_code"]),
                error_message=str(payload["error_message"]),
                details=dict(payload.get("details", {})),
                suggest=suggest or [],
            ),
            metadata=metadata or {},
        )