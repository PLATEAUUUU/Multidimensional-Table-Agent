"""
tool的hook基类

创建时间：2025/5/1
开发人：zcry
"""
from __future__ import annotations

from abc import ABC

from app.core.hooks.context import (
    ToolAfterHookPayload,
    ToolBeforeHookPayload,
    ToolErrorHookPayload,
    ToolHookRuntimeContext,
)


class BaseToolHook(ABC):
    """
    Tool hook 协议

    设计原则：
    1. ToolRuntime 负责固定执行协议
    2. hook 负责可插拔增强
    3. hook 默认 fail-open，不影响主流程
    4. hook 不应重复承担 schema 校验、输出校验、错误归一化职责
    """

    async def before_tool_call(
        self,
        runtime_ctx: ToolHookRuntimeContext,
        payload: ToolBeforeHookPayload,
    ) -> ToolBeforeHookPayload | None:
        """
        在工具调用前执行

        返回：
        - None：表示不修改 payload
        - ToolBeforeHookPayload：表示使用新的 payload 继续执行

        建议：权限检查、安全审计、补充 metadata、参数脱敏/轻量补值
        """
        return None

    async def after_tool_call(
        self,
        runtime_ctx: ToolHookRuntimeContext,
        payload: ToolAfterHookPayload,
    ) -> ToolAfterHookPayload | None:
        """
        在工具返回 ToolResult 后执行

        返回：
        - None：表示不修改 payload
        - ToolAfterHookPayload：表示使用新的 payload 继续执行

        建议：结果审计、结果脱敏、附加 metadata、轻量后处理
        """
        return None

    async def on_tool_error(
        self,
        runtime_ctx: ToolHookRuntimeContext,
        payload: ToolErrorHookPayload,
    ) -> ToolErrorHookPayload | None:
        """
        在工具异常归一化为 ToolError 后执行

        返回：
        - None：表示不修改 payload
        - ToolErrorHookPayload：表示使用新的 payload 继续执行

        建议：错误审计、补充错误 details、改善 suggest、做告警/记录
        """
        return None
