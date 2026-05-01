"""
hook 上下文定义

创建时间：2026/5/1
开发人：zcry
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.agents.interview_state import InterviewState
from app.core.tools.errors import ToolError
from app.core.tools.result import ToolCallContext, ToolResult


class HookRuntimeContext(BaseModel):
    """
    通用 hook 运行时上下文

    说明：
    - 这里只放稳定的身份信息
    - 不放会在不同阶段变化的 payload
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    trace_id: str = Field(..., description="链路追踪 ID")
    run_id: str = Field(..., description="当前执行 ID")


class AgentHookRuntimeContext(HookRuntimeContext):
    """
    Agent hook 的稳定运行时上下文
    """

    agent_name: str = Field(..., description="当前 Agent 名称")
    model_name: str = Field(..., description="当前 Agent 使用的模型名")


class ToolHookRuntimeContext(HookRuntimeContext):
    """
    Tool hook 的稳定运行时上下文

    说明：
    - 这里复用 ToolCallContext 里的核心身份信息
    """

    tool_name: str = Field(..., description="工具名称")
    agent_name: str | None = Field(default=None, description="调用该工具的 Agent 名称")
    tool_call_id: str | None = Field(default=None, description="单次工具调用 ID")


class AgentBeforeHookPayload(BaseModel):
    """
    Agent 执行前的 payload
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    state: InterviewState = Field(..., description="当前 Agent 输入状态")


class AgentAfterHookPayload(BaseModel):
    """
    Agent 成功完成后的 payload
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    state: InterviewState = Field(..., description="当前 Agent 输入状态")
    patch: dict[str, Any] = Field(..., description="Agent 输出 patch")


class AgentErrorHookPayload(BaseModel):
    """
    Agent 异常阶段的 payload
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    state: InterviewState = Field(..., description="当前 Agent 输入状态")
    error: Exception = Field(..., description="当前异常对象")


class ToolBeforeHookPayload(BaseModel):
    """
    Tool 执行前的 payload

    注意：
    - 这里保留 raw_args，主要用于审计、权限检查、轻量补充
    - 不建议 hook 在这里承担 schema 校验职责
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    raw_args: dict[str, Any] = Field(..., description="原始输入参数")


class ToolAfterHookPayload(BaseModel):
    """
    Tool 执行完成后的 payload
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    result: ToolResult = Field(..., description="工具执行结果")


class ToolErrorHookPayload(BaseModel):
    """
    Tool 异常阶段的 payload
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    raw_args: dict[str, Any] = Field(..., description="原始输入参数")
    error: ToolError = Field(..., description="归一化后的工具错误")
