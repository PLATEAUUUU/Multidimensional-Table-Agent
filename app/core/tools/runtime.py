"""
工具执行外壳

创建时间：2026/4/29
开发人：zcry
"""

"""
工具执行外壳（Tool Runtime）

职责：
1. 统一工具输入校验
2. 统一 observer 埋点
3. 统一耗时统计
4. 统一错误归一化
5. 统一 suggest 生成
6. 统一 ToolResult / ToolCallRecord 构造

说明：
- runtime 不直接抛 ToolError 给上层，默认返回失败 ToolResult
- 是否把最终失败升级成 AgentError，由 Agent 层决定
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.core.hooks.context import (
    ToolAfterHookPayload,
    ToolBeforeHookPayload,
    ToolErrorHookPayload,
    ToolHookRuntimeContext,
)

from app.core.hooks.registry import HookRegistry
from app.core.agent.observer import AgentObserver
from app.core.tools.errors import (
    ToolError,
    ToolExecutionError,
    ToolInputError,
    ToolOutputValidationError,
    ToolTimeoutError,
    ToolUnavailableError,
    normalize_tool_error,
)
from app.core.tools.result import ToolCallContext, ToolCallRecord, ToolResult
from app.tools.base import BaseTool, ToolInput


ToolRecordSink = Callable[[ToolCallRecord], None | Awaitable[None]]


class ToolRuntime:
    """
    工具统一执行运行时

    职责：
        1. 统一工具输入校验
        2. 统一 observer 埋点
        3. 统一耗时统计
        4. 统一错误归一化
        5. 统一 suggest 生成
        6. 统一 ToolResult / ToolCallRecord 构造
        7. 在固定执行协议上挂接可插拔 hooks
    """

    def __init__(
        self,
        observer: AgentObserver,
        *,
        record_sink: ToolRecordSink | None = None,
        hook_registry: HookRegistry | None = None,
        default_max_attempts: int = 1,
    ) -> None:
        self.observer = observer
        self.record_sink = record_sink
        self.hook_registry = hook_registry
        self.default_max_attempts = max(1, default_max_attempts)

    async def invoke(
        self,
        tool: BaseTool[Any],
        raw_args: Mapping[str, Any] | BaseModel,
        context: ToolCallContext,
        *,
        max_attempts: int | None = None,
    ) -> ToolResult:
        """
        统一工具调用入口

        参数说明：
        - tool: 工具实例
        - raw_args: 原始参数（通常是 dict，也支持已构造好的 Pydantic model）
        - context: 工具调用上下文
        - max_attempts: 最大尝试次数，默认使用 runtime 配置

        返回：
        - 成功返回 ToolResult(success=True, ...)
        - 失败返回 ToolResult(success=False, ...)
        """
        started_at = self._utcnow()
        attempts = max(1, max_attempts or self.default_max_attempts)
        runtime_ctx = self._build_tool_hook_runtime_context(context)

        original_arguments = self._serialize_args(raw_args)
        before_payload = await self._run_before_tool_hooks(
            runtime_ctx=runtime_ctx,
            raw_args=original_arguments,
        )
        effective_arguments = dict(before_payload.raw_args)

        self.observer.record_tool_call(
            tool_name=tool.name,
            trace_id=context.trace_id,
            metadata={
                "run_id": context.run_id,
                "agent_name": context.agent_name,
                "tool_call_id": getattr(context, "tool_call_id", None),
                "arguments": effective_arguments,
                "max_attempts": attempts,
            },
        )

        try:
            parsed_args = self._validate_input(tool, effective_arguments)
        except Exception as exc:
            duration_ms = self._elapsed_ms_from(started_at)
            normalized_error = normalize_tool_error(exc, tool_name=tool.name)
            normalized_error = await self._run_tool_error_hooks(
                runtime_ctx=runtime_ctx,
                raw_args=effective_arguments,
                error=normalized_error,
            )

            result = self._build_failure_result(
                tool=tool,
                context=context,
                error=normalized_error,
                raw_args=effective_arguments,
                duration_ms=duration_ms,
                attempt=1,
                max_attempts=attempts,
            )
            result = await self._run_after_tool_hooks(runtime_ctx=runtime_ctx, result=result)

            record = self._build_call_record(
                context=context,
                arguments=effective_arguments,
                started_at=started_at,
                duration_ms=duration_ms,
                result=result,
            )
            await self._emit_record(record)
            self._record_tool_result(result, attempt=1, max_attempts=attempts)
            return result

        last_error: ToolError | None = None

        for attempt in range(1, attempts + 1):
            try:
                output = await self._execute_tool(tool, parsed_args)
                duration_ms = self._elapsed_ms_from(started_at)

                result = ToolResult.ok(
                    context=context,
                    data=output,
                    duration_ms=duration_ms,
                    metadata={
                        "attempt": attempt,
                        "max_attempts": attempts,
                    },
                )
                result = await self._run_after_tool_hooks(runtime_ctx=runtime_ctx, result=result)

                record = self._build_call_record(
                    context=context,
                    arguments=effective_arguments,
                    started_at=started_at,
                    duration_ms=duration_ms,
                    result=result,
                )
                await self._emit_record(record)
                self._record_tool_result(result, attempt=attempt, max_attempts=attempts)
                return result

            except Exception as exc:
                last_error = normalize_tool_error(exc, tool_name=tool.name)
                last_error = await self._run_tool_error_hooks(
                    runtime_ctx=runtime_ctx,
                    raw_args=effective_arguments,
                    error=last_error,
                )

                if attempt < attempts and self._should_retry(last_error, attempt, attempts):
                    continue

                duration_ms = self._elapsed_ms_from(started_at)
                result = self._build_failure_result(
                    tool=tool,
                    context=context,
                    error=last_error,
                    raw_args=effective_arguments,
                    duration_ms=duration_ms,
                    attempt=attempt,
                    max_attempts=attempts,
                )
                result = await self._run_after_tool_hooks(runtime_ctx=runtime_ctx, result=result)

                record = self._build_call_record(
                    context=context,
                    arguments=effective_arguments,
                    started_at=started_at,
                    duration_ms=duration_ms,
                    result=result,
                )
                await self._emit_record(record)
                self._record_tool_result(result, attempt=attempt, max_attempts=attempts)
                return result

        fallback_error = last_error or ToolExecutionError(
            "Tool execution failed with unknown state",
            tool_name=tool.name,
        )
        fallback_error = await self._run_tool_error_hooks(
            runtime_ctx=runtime_ctx,
            raw_args=effective_arguments,
            error=fallback_error,
        )

        duration_ms = self._elapsed_ms_from(started_at)
        result = self._build_failure_result(
            tool=tool,
            context=context,
            error=fallback_error,
            raw_args=effective_arguments,
            duration_ms=duration_ms,
            attempt=attempts,
            max_attempts=attempts,
        )
        result = await self._run_after_tool_hooks(runtime_ctx=runtime_ctx, result=result)

        record = self._build_call_record(
            context=context,
            arguments=effective_arguments,
            started_at=started_at,
            duration_ms=duration_ms,
            result=result,
        )
        await self._emit_record(record)
        self._record_tool_result(result, attempt=attempts, max_attempts=attempts)
        return result

    def _validate_input(
        self,
        tool: BaseTool[Any],
        raw_args: Mapping[str, Any] | BaseModel,
    ) -> ToolInput | BaseModel:
        """
        统一输入校验入口

        约定：
        1. 优先从 tool.input_model 读取 schema
        2. 如果 raw_args 已经是 BaseModel，直接复用
        3. 如果 tool 没声明 input_model 且传入的是 dict，则认为工具定义不完整
        """
        if isinstance(raw_args, BaseModel):
            return raw_args

        input_model = self._resolve_input_model(tool)
        if input_model is None:
            raise ToolInputError(
                f"Tool '{tool.name}' must declare input_model to validate mapping arguments",
                tool_name=tool.name,
                details={"received_args_type": type(raw_args).__name__},
            )

        try:
            return input_model.model_validate(dict(raw_args))
        except Exception as exc:
            raise normalize_tool_error(exc, tool_name=tool.name) from exc

    async def _execute_tool(
        self,
        tool: BaseTool[Any],
        parsed_args: ToolInput | BaseModel,
    ) -> dict[str, Any]:
        """
        真正执行工具本体
        这里不做业务逻辑，只负责调用工具接口并做最基本的输出约束
        """
        result = await tool.ainvoke(parsed_args)  # type: ignore[arg-type]

        if not isinstance(result, dict):
            raise ToolOutputValidationError(
                f"Tool '{tool.name}' returned invalid output type: expected dict",
                tool_name=tool.name,
                details={"actual_type": type(result).__name__},
            )

        return result

    def _resolve_input_model(self, tool: BaseTool[Any]) -> type[ToolInput] | None:
        """
        从工具实例读取输入 schema
        """
        input_model = getattr(tool, "input_model", None)
        if input_model is None:
            return None

        if not inspect.isclass(input_model):
            raise ToolInputError(
                f"Tool '{tool.name}' has invalid input_model: expected class",
                tool_name=tool.name,
            )

        if not issubclass(input_model, ToolInput):
            raise ToolInputError(
                f"Tool '{tool.name}' input_model must inherit from ToolInput",
                tool_name=tool.name,
                details={"input_model": input_model.__name__},
            )

        return input_model

    def _should_retry(
        self,
        error: ToolError,
        attempt: int,
        max_attempts: int,
    ) -> bool:
        """
        工具重试策略

        当前保守策略：
        - ToolTimeoutError：允许重试
        - ToolExecutionError：允许重试
        - 其他错误：不重试
        """
        if attempt >= max_attempts:
            return False

        return isinstance(error, (ToolTimeoutError, ToolExecutionError))

    def _build_suggestions(
        self,
        tool: BaseTool[Any],
        error: ToolError,
        raw_args: dict[str, Any],
        context: ToolCallContext,
        *,
        attempt: int,
        max_attempts: int,
    ) -> list[str]:
        """
        根据工具、错误和上下文生成建议动作
        """
        suggestions: list[str] = []

        if isinstance(error, ToolInputError):
            suggestions.extend(
                [
                    "检查工具输入参数是否完整。",
                    "核对字段名、字段类型和必填项是否与 input_model 一致。",
                ]
            )
        elif isinstance(error, ToolOutputValidationError):
            suggestions.extend(
                [
                    "检查工具返回结构是否符合调用方约定。",
                    "确认工具输出字段是否缺失或类型不匹配。",
                ]
            )
        elif isinstance(error, ToolTimeoutError):
            suggestions.extend(
                [
                    "检查外部依赖是否响应过慢。",
                    "必要时提高 timeout，或稍后再试。",
                ]
            )
        elif isinstance(error, ToolUnavailableError):
            suggestions.extend(
                [
                    "检查工具依赖的配置、环境变量或外部服务是否可用。",
                ]
            )
        elif isinstance(error, ToolExecutionError):
            suggestions.extend(
                [
                    "查看底层执行错误和 details 字段定位根因。",
                ]
            )

        if attempt < max_attempts:
            suggestions.append(f"当前为第 {attempt} 次失败，仍可继续重试。")
        else:
            suggestions.append("已耗尽本次工具调用重试预算，建议由 Agent 层决定是否升级为 AgentError。")

        return suggestions

    def _build_failure_result(
        self,
        *,
        tool: BaseTool[Any],
        context: ToolCallContext,
        error: ToolError,
        raw_args: dict[str, Any],
        duration_ms: int,
        attempt: int,
        max_attempts: int,
    ) -> ToolResult:
        """
        统一构造失败 ToolResult。
        """
        suggest = self._build_suggestions(
            tool,
            error,
            raw_args,
            context,
            attempt=attempt,
            max_attempts=max_attempts,
        )

        return ToolResult.fail(
            context=context,
            error=error,
            duration_ms=duration_ms,
            suggest=suggest,
            metadata={
                "attempt": attempt,
                "max_attempts": max_attempts,
            },
        )

    def _build_call_record(
        self,
        *,
        context: ToolCallContext,
        arguments: dict[str, Any],
        started_at: datetime,
        duration_ms: int,
        result: ToolResult,
    ) -> ToolCallRecord:
        finished_at = self._utcnow()
        return ToolCallRecord(
            context=context,
            arguments=arguments,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            result=result,
        )

    def _record_tool_result(
        self,
        result: ToolResult,
        *,
        attempt: int,
        max_attempts: int,
    ) -> None:
        metadata: dict[str, Any] = {
            "run_id": result.run_id,
            "agent_name": result.agent_name,
            "duration_ms": result.duration_ms,
            "attempt": attempt,
            "max_attempts": max_attempts,
        }

        if result.success:
            metadata["result"] = self._summarize_data(result.data)
        else:
            metadata["error"] = result.error.model_dump() if result.error else None

        self.observer.record_tool_result(
            tool_name=result.tool_name,
            trace_id=result.trace_id,
            success=result.success,
            metadata=metadata,
        )

    async def _emit_record(self, record: ToolCallRecord) -> None:
        if self.record_sink is None:
            return

        maybe_awaitable = self.record_sink(record)
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable

    async def _run_before_tool_hooks(
        self,
        *,
        runtime_ctx: ToolHookRuntimeContext,
        raw_args: dict[str, Any],
    ) -> ToolBeforeHookPayload:
        if self.hook_registry is None:
            return ToolBeforeHookPayload(raw_args=raw_args)

        payload = ToolBeforeHookPayload(raw_args=raw_args)
        return await self.hook_registry.run_before_tool_call(runtime_ctx, payload)

    async def _run_after_tool_hooks(
        self,
        *,
        runtime_ctx: ToolHookRuntimeContext,
        result: ToolResult,
    ) -> ToolResult:
        if self.hook_registry is None:
            return result

        payload = ToolAfterHookPayload(result=result)
        payload = await self.hook_registry.run_after_tool_call(runtime_ctx, payload)
        return payload.result

    async def _run_tool_error_hooks(
        self,
        *,
        runtime_ctx: ToolHookRuntimeContext,
        raw_args: dict[str, Any],
        error: ToolError,
    ) -> ToolError:
        if self.hook_registry is None:
            return error

        payload = ToolErrorHookPayload(raw_args=raw_args, error=error)
        payload = await self.hook_registry.run_on_tool_error(runtime_ctx, payload)
        return payload.error

    def _build_tool_hook_runtime_context(
        self,
        context: ToolCallContext,
    ) -> ToolHookRuntimeContext:
        return ToolHookRuntimeContext(
            trace_id=context.trace_id,
            run_id=context.run_id,
            tool_name=context.tool_name,
            agent_name=context.agent_name,
            tool_call_id=getattr(context, "tool_call_id", None),
        )

    def _serialize_args(self, raw_args: Mapping[str, Any] | BaseModel) -> dict[str, Any]:
        if isinstance(raw_args, BaseModel):
            return raw_args.model_dump()
        return dict(raw_args)

    def _summarize_data(self, data: Any) -> Any:
        return data

    def _elapsed_ms_from(self, started_at: datetime) -> int:
        return max(0, int((self._utcnow() - started_at).total_seconds() * 1000))

    def _utcnow(self) -> datetime:
        return datetime.now(timezone.utc)