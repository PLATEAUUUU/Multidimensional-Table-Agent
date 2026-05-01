"""
hooks 注册中心

创建时间：2026/5/1
开发人：zcry
"""
from __future__ import annotations

import logging

from app.core.hooks.context import (
    AgentAfterHookPayload,
    AgentBeforeHookPayload,
    AgentErrorHookPayload,
    AgentHookRuntimeContext,
    ToolAfterHookPayload,
    ToolBeforeHookPayload,
    ToolErrorHookPayload,
    ToolHookRuntimeContext,
)
from app.hooks.agent.base import BaseAgentHook
from app.hooks.tools.base import BaseToolHook


class HookRegistry:
    """
    Hook 注册与分发中心

    当前职责：
    1. 注册 agent hooks
    2. 注册 tool hooks
    3. 按注册顺序分发 hook
    4. hook 自身异常默认 fail-open，只记录日志，不打断主流程
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._agent_hooks: list[BaseAgentHook] = []
        self._tool_hooks: list[BaseToolHook] = []

    # ============================================================
    # Register
    # ============================================================

    def register_agent_hook(self, hook: BaseAgentHook) -> None:
        self._agent_hooks.append(hook)

    def register_tool_hook(self, hook: BaseToolHook) -> None:
        self._tool_hooks.append(hook)

    def register_agent_hooks(self, hooks: list[BaseAgentHook]) -> None:
        for hook in hooks:
            self.register_agent_hook(hook)

    def register_tool_hooks(self, hooks: list[BaseToolHook]) -> None:
        for hook in hooks:
            self.register_tool_hook(hook)

    def clear(self) -> None:
        """
        清空所有已注册 hooks
        """
        self._agent_hooks.clear()
        self._tool_hooks.clear()

    # ============================================================
    # List
    # ============================================================

    def list_agent_hooks(self) -> list[BaseAgentHook]:
        return list(self._agent_hooks)

    def list_tool_hooks(self) -> list[BaseToolHook]:
        return list(self._tool_hooks)

    # ============================================================
    # Agent lifecycle
    # ============================================================

    async def run_before_agent_run(
        self,
        runtime_ctx: AgentHookRuntimeContext,
        payload: AgentBeforeHookPayload,
    ) -> AgentBeforeHookPayload:
        current = payload

        for hook in self._agent_hooks:
            try:
                updated = await hook.before_agent_run(runtime_ctx, current)
                if updated is not None:
                    current = updated
            except Exception as exc:
                self.logger.warning(
                    "before_agent_run hook failed: hook=%s agent=%s run_id=%s error=%s",
                    hook.__class__.__name__,
                    runtime_ctx.agent_name,
                    runtime_ctx.run_id,
                    exc,
                )

        return current

    async def run_after_agent_run(
        self,
        runtime_ctx: AgentHookRuntimeContext,
        payload: AgentAfterHookPayload,
    ) -> AgentAfterHookPayload:
        current = payload

        for hook in self._agent_hooks:
            try:
                updated = await hook.after_agent_run(runtime_ctx, current)
                if updated is not None:
                    current = updated
            except Exception as exc:
                self.logger.warning(
                    "after_agent_run hook failed: hook=%s agent=%s run_id=%s error=%s",
                    hook.__class__.__name__,
                    runtime_ctx.agent_name,
                    runtime_ctx.run_id,
                    exc,
                )

        return current

    async def run_on_agent_error(
        self,
        runtime_ctx: AgentHookRuntimeContext,
        payload: AgentErrorHookPayload,
    ) -> AgentErrorHookPayload:
        current = payload

        for hook in self._agent_hooks:
            try:
                updated = await hook.on_agent_error(runtime_ctx, current)
                if updated is not None:
                    current = updated
            except Exception as exc:
                self.logger.warning(
                    "on_agent_error hook failed: hook=%s agent=%s run_id=%s error=%s",
                    hook.__class__.__name__,
                    runtime_ctx.agent_name,
                    runtime_ctx.run_id,
                    exc,
                )

        return current

    # ============================================================
    # Tool lifecycle
    # ============================================================

    async def run_before_tool_call(
        self,
        runtime_ctx: ToolHookRuntimeContext,
        payload: ToolBeforeHookPayload,
    ) -> ToolBeforeHookPayload:
        current = payload

        for hook in self._tool_hooks:
            try:
                updated = await hook.before_tool_call(runtime_ctx, current)
                if updated is not None:
                    current = updated
            except Exception as exc:
                self.logger.warning(
                    "before_tool_call hook failed: hook=%s tool=%s run_id=%s error=%s",
                    hook.__class__.__name__,
                    runtime_ctx.tool_name,
                    runtime_ctx.run_id,
                    exc,
                )

        return current

    async def run_after_tool_call(
        self,
        runtime_ctx: ToolHookRuntimeContext,
        payload: ToolAfterHookPayload,
    ) -> ToolAfterHookPayload:
        current = payload

        for hook in self._tool_hooks:
            try:
                updated = await hook.after_tool_call(runtime_ctx, current)
                if updated is not None:
                    current = updated
            except Exception as exc:
                self.logger.warning(
                    "after_tool_call hook failed: hook=%s tool=%s run_id=%s error=%s",
                    hook.__class__.__name__,
                    runtime_ctx.tool_name,
                    runtime_ctx.run_id,
                    exc,
                )

        return current

    async def run_on_tool_error(
        self,
        runtime_ctx: ToolHookRuntimeContext,
        payload: ToolErrorHookPayload,
    ) -> ToolErrorHookPayload:
        current = payload

        for hook in self._tool_hooks:
            try:
                updated = await hook.on_tool_error(runtime_ctx, current)
                if updated is not None:
                    current = updated
            except Exception as exc:
                self.logger.warning(
                    "on_tool_error hook failed: hook=%s tool=%s run_id=%s error=%s",
                    hook.__class__.__name__,
                    runtime_ctx.tool_name,
                    runtime_ctx.run_id,
                    exc,
                )

        return current
