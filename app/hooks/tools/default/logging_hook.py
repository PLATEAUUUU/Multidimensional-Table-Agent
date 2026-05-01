from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from app.core.tools.errors import ToolError
from app.core.tools.result import ToolCallContext, ToolResult
from app.hooks.tools.base import BaseToolHook


class LoggingToolHook(BaseToolHook):
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    async def before_tool_call(
        self,
        context: ToolCallContext,
        raw_args: Mapping[str, Any] | BaseModel,
    ) -> Mapping[str, Any] | BaseModel | None:
        self.logger.info(
            "before_tool_call tool=%s run_id=%s tool_call_id=%s",
            context.tool_name,
            context.run_id,
            context.tool_call_id,
        )
        return None

    async def after_tool_call(
        self,
        context: ToolCallContext,
        result: ToolResult,
    ) -> ToolResult | None:
        self.logger.info(
            "after_tool_call tool=%s success=%s run_id=%s tool_call_id=%s",
            context.tool_name,
            result.success,
            context.run_id,
            context.tool_call_id,
        )
        return None

    async def on_tool_error(
        self,
        context: ToolCallContext,
        error: ToolError,
        raw_args: Mapping[str, Any] | BaseModel,
    ) -> ToolError | None:
        self.logger.warning(
            "on_tool_error tool=%s error_code=%s run_id=%s tool_call_id=%s",
            context.tool_name,
            error.error_code,
            context.run_id,
            context.tool_call_id,
        )
        return None
