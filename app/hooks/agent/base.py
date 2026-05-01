"""
hooks base定义

创建时间：2026/5/1
开发人：zcry
"""

from __future__ import annotations

from abc import ABC

from app.core.hooks.context import (
    AgentAfterHookPayload,
    AgentBeforeHookPayload,
    AgentErrorHookPayload,
    AgentHookRuntimeContext,
)


class BaseAgentHook(ABC):
    """
    Agent hook 协议

    设计原则：
    1. BaseAgent 负责固定执行协议
    2. hook 负责可插拔增强
    3. hook 默认 fail-open，不应轻易打断主流程
    4. runtime_ctx 负责稳定身份信息
    5. payload 负责当前阶段数据
    """

    async def before_agent_run(
        self,
        runtime_ctx: AgentHookRuntimeContext,
        payload: AgentBeforeHookPayload,
    ) -> AgentBeforeHookPayload | None:
        """
        在 Agent 正式执行前调用

        返回：
        - None：表示不修改 payload
        - AgentBeforeHookPayload：表示使用新的payload继续执行
        """
        return None

    async def after_agent_run(
        self,
        runtime_ctx: AgentHookRuntimeContext,
        payload: AgentAfterHookPayload,
    ) -> AgentAfterHookPayload | None:
        """
        在 Agent 成功生成 patch 后调用。

        返回：
        - None：表示不修改 payload
        - AgentAfterHookPayload：表示使用新的 payload 继续执行
        """
        return None

    async def on_agent_error(
        self,
        runtime_ctx: AgentHookRuntimeContext,
        payload: AgentErrorHookPayload,
    ) -> AgentErrorHookPayload | None:
        """
        在 Agent 执行异常后调用。

        返回：
        - None：表示不修改 payload
        - AgentErrorHookPayload：表示使用新的 payload 继续执行
        """
        return None
