# app/agents/base.py
"""
LangGraph Agent基类

创建时间：2026/4/28
开发人：zcry
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from contextvars import Token
from time import perf_counter
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app.agents.interview_state import InterviewState
from app.core.agent.errors import BizException, ErrorCode
from app.core.agent.observer import (
    AgentObserver,
    reset_run_id,
    reset_trace_id,
    set_run_id,
    set_trace_id,
)
from app.core.agent.security import ContentSafetyInterceptor, SecurityInterceptionError
from app.core.hooks.context import (
    AgentAfterHookPayload,
    AgentBeforeHookPayload,
    AgentErrorHookPayload,
    AgentHookRuntimeContext,
)
from app.core.hooks.registry import HookRegistry
from app.core.skills.runtime import SkillRuntime
from app.core.tools.registry import ToolRegistry
from app.core.tools.result import ToolCallContext, ToolResult
from app.core.tools.runtime import ToolRuntime
from app.models.dto.skill.skill import SkillApplyResult


OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseAgent(ABC, Generic[OutputT]):
    """
    Agent 运行时外壳（Harness）

    当前职责：
    1. 管理 agent 生命周期
    2. 统一输入 / 输出安全检查
    3. 统一 observer 埋点
    4. 统一 hook 生命周期
    5. 提供 tool / skill 调用助手方法
    """

    agent_name: str = ""
    allowed_tools: list[str] | None = None
    allowed_skills: list[str] | None = None
    output_model: type[OutputT] | None = None

    def __init__(
        self,
        model_name: str,
        observer: AgentObserver,
        prompt_template: str,
        *,
        tool_registry: ToolRegistry | None = None,
        tool_runtime: ToolRuntime | None = None,
        skill_runtime: SkillRuntime | None = None,
        hook_registry: HookRegistry | None = None,
        safety_interceptor: ContentSafetyInterceptor | None = None,
    ) -> None:
        if not self.agent_name:
            raise ValueError(f"{self.__class__.__name__} 必须定义 agent_name")

        self.model_name = model_name
        self.observer = observer
        self.prompt_template = prompt_template

        self.tool_registry = tool_registry
        self.tool_runtime = tool_runtime
        self.skill_runtime = skill_runtime
        self.hook_registry = hook_registry

        self.safety_interceptor = safety_interceptor or ContentSafetyInterceptor()
        self.logger = logging.getLogger(f"agent.{self.agent_name}")

    async def __call__(self, state: InterviewState) -> dict[str, Any]:
        """Agent 统一执行入口"""
        started_at = perf_counter()

        trace_id = state.get("trace_id") or self.observer.new_trace_id()
        run_id = uuid4().hex

        trace_token: Token[str] = set_trace_id(trace_id)
        run_token: Token[str] = set_run_id(run_id)

        base_metadata = {
            "run_id": run_id,
            "candidate_id": state.get("candidate_id"),
            "current_round": str(state.get("current_round")),
            "process_status": str(state.get("process_status")),
            "active_agent": state.get("active_agent"),
        }

        runtime_ctx = AgentHookRuntimeContext(
            trace_id=trace_id,
            run_id=run_id,
            agent_name=self.agent_name,
            model_name=self.model_name,
        )

        self.observer.record_agent_call(
            agent_name=self.agent_name,
            trace_id=trace_id,
            metadata=base_metadata,
        )

        try:
            before_payload = AgentBeforeHookPayload(state=state)
            if self.hook_registry is not None:
                before_payload = await self.hook_registry.run_before_agent_run(
                    runtime_ctx,
                    before_payload,
                )
            effective_state = before_payload.state

            await self._preflight(effective_state)

            raw_output = await self._run(effective_state)
            normalized_output = self._normalize_output(raw_output)

            await self._audit_output(normalized_output)

            patch = self._to_state_patch(normalized_output)
            if not isinstance(patch, dict):
                raise TypeError(f"{self.agent_name}._to_state_patch 必须返回 dict[str, Any]")

            patch["trace_id"] = trace_id
            patch["run_id"] = run_id
            patch["active_agent"] = self.agent_name
            patch["is_safe"] = True

            patch["token_usage"] = self.observer.record_token_usage(
                self.agent_name,
                trace_id,
                patch.get("token_usage"),
            )

            after_payload = AgentAfterHookPayload(
                state=effective_state,
                patch=patch,
            )
            if self.hook_registry is not None:
                after_payload = await self.hook_registry.run_after_agent_run(
                    runtime_ctx,
                    after_payload,
                )
            patch = after_payload.patch

            duration_ms = int((perf_counter() - started_at) * 1000)

            self.observer.record_agent_success(
                agent_name=self.agent_name,
                trace_id=trace_id,
                metadata={
                    **base_metadata,
                    "duration_ms": duration_ms,
                    "output_mode": "structured"
                    if isinstance(normalized_output, BaseModel)
                    else "patch",
                    "patch_keys": sorted(patch.keys()),
                },
            )

            return patch

        except SecurityInterceptionError as exc:
            duration_ms = int((perf_counter() - started_at) * 1000)

            if self.hook_registry is not None:
                error_payload = await self.hook_registry.run_on_agent_error(
                    runtime_ctx,
                    AgentErrorHookPayload(state=state, error=exc),
                )
                exc = error_payload.error if isinstance(error_payload.error, Exception) else exc

            self.observer.record_agent_failure(
                agent_name=self.agent_name,
                trace_id=trace_id,
                error=exc,
                metadata={
                    **base_metadata,
                    "duration_ms": duration_ms,
                    "stage": "security",
                },
            )
            raise

        except ValidationError as exc:
            duration_ms = int((perf_counter() - started_at) * 1000)

            if self.hook_registry is not None:
                error_payload = await self.hook_registry.run_on_agent_error(
                    runtime_ctx,
                    AgentErrorHookPayload(state=state, error=exc),
                )
                if isinstance(error_payload.error, ValidationError):
                    exc = error_payload.error

            self.observer.record_agent_failure(
                agent_name=self.agent_name,
                trace_id=trace_id,
                error=exc,
                metadata={
                    **base_metadata,
                    "duration_ms": duration_ms,
                    "stage": "output_validation",
                },
            )

            self.logger.exception("Agent output validation failed: %s", self.agent_name)
            raise BizException(
                ErrorCode.AGENT_OUTPUT_VALIDATION_FAILED,
                message=f"{self.agent_name} 输出结构校验失败",
                data={"errors": exc.errors()},
            ) from exc

        except Exception as exc:
            duration_ms = int((perf_counter() - started_at) * 1000)

            if self.hook_registry is not None:
                error_payload = await self.hook_registry.run_on_agent_error(
                    runtime_ctx,
                    AgentErrorHookPayload(state=state, error=exc),
                )
                exc = error_payload.error if isinstance(error_payload.error, Exception) else exc

            self.observer.record_agent_failure(
                agent_name=self.agent_name,
                trace_id=trace_id,
                error=exc,
                metadata={
                    **base_metadata,
                    "duration_ms": duration_ms,
                    "stage": "execution",
                },
            )

            self.logger.exception("Agent execution failed: %s", self.agent_name)
            if isinstance(exc, BizException):
                raise

            raise BizException(
                ErrorCode.AGENT_EXECUTION_FAILED,
                message=f"{self.agent_name} 执行失败",
                data={
                    "agent_name": self.agent_name,
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            ) from exc

        finally:
            reset_run_id(run_token)
            reset_trace_id(trace_token)

    async def _preflight(self, state: InterviewState) -> None:
        """输入安全检查"""
        allowed = await self.safety_interceptor.preflight_agent_input(
            self.agent_name,
            state,
        )
        if not allowed:
            raise SecurityInterceptionError(f"Input rejected for agent {self.agent_name}")

    async def _audit_output(self, output: OutputT | dict[str, Any]) -> None:
        """输出安全检查"""
        if isinstance(output, BaseModel):
            payload = output.model_dump()
        else:
            payload = dict(output)

        allowed = await self.safety_interceptor.audit_agent_output(
            self.agent_name,
            payload,
        )
        if not allowed:
            raise SecurityInterceptionError(f"Output rejected for agent {self.agent_name}")

    def _normalize_output(
        self,
        raw_output: dict[str, Any] | BaseModel,
    ) -> OutputT | dict[str, Any]:
        if self.output_model is None:
            if not isinstance(raw_output, Mapping):
                raise TypeError(
                    f"{self.agent_name} 未声明 output_model 时，_run 必须返回 dict[str, Any]"
                )
            return dict(raw_output)

        if isinstance(raw_output, self.output_model):
            return raw_output

        return self.output_model.model_validate(raw_output)

    def _to_state_patch(self, output: OutputT | dict[str, Any]) -> dict[str, Any]:
        if isinstance(output, BaseModel):
            return {
                "latest_agent_output": output,
            }
        return dict(output)

    async def _invoke_tool(
        self,
        tool_name: str,
        raw_args: Mapping[str, Any] | BaseModel,
    ) -> ToolResult:
        """
        统一工具调用助手。

        子类在 _run(...) 里不应直接调用 tool.ainvoke(...)，
        而应统一走这个入口。
        """
        if self.tool_registry is None or self.tool_runtime is None:
            raise BizException(
                ErrorCode.INTERNAL_ERROR,
                message=f"{self.agent_name} 未配置 tool runtime",
            )

        tool = self.tool_registry.get(
            tool_name,
            requester_agent=self.agent_name,
            allowed_tools=self.allowed_tools,
        )

        context = ToolCallContext(
            trace_id=self.observer.ensure_trace_id(None),
            run_id=run_id_or_raise(),
            tool_name=tool.name,
            agent_name=self.agent_name,
            tool_call_id=uuid4().hex,
        )

        result = await self.tool_runtime.invoke(
            tool,
            raw_args,
            context,
        )

        if not result.success:
            raise self._tool_result_to_biz_exception(result)

        return result

    def _build_skill_catalog_prompt(self) -> str:
        """
        构造当前 agent 可见的 skill catalog prompt。
        """
        if self.skill_runtime is None:
            return ""

        return self.skill_runtime.build_catalog_prompt(
            requester_agent=self.agent_name,
            allowed_skills=self.allowed_skills,
        )

    async def _apply_skill(self, skill_name: str) -> SkillApplyResult:
        """
        应用某个 skill，并在必要时做安全校验。
        """
        if self.skill_runtime is None:
            raise BizException(
                ErrorCode.INTERNAL_ERROR,
                message=f"{self.agent_name} 未配置 skill runtime",
            )

        allowed = await self.safety_interceptor.validate_skill_invocation(
            skill_name=skill_name,
            agent_name=self.agent_name,
            allowed_skills=self.allowed_skills,
        )
        if not allowed:
            raise BizException(
                ErrorCode.AGENT_SECURITY_BLOCKED,
                message=f"{self.agent_name} 不允许调用 skill: {skill_name}",
            )

        return self.skill_runtime.apply_skill(
            skill_name,
            requester_agent=self.agent_name,
            allowed_skills=self.allowed_skills,
        )

    def _build_prompt(
        self,
        *,
        skill_result: SkillApplyResult | None = None,
        extra_sections: list[str] | None = None,
    ) -> str:
        """
        默认 prompt 拼装助手：
        - prompt_template
        - skill catalog
        - applied skill prompt
        - extra sections
        """
        sections = [self.prompt_template]

        skill_catalog = self._build_skill_catalog_prompt()
        if skill_catalog:
            sections.append(skill_catalog)

        if skill_result is not None and skill_result.prompt_injection.strip():
            sections.append(skill_result.prompt_injection)

        for section in extra_sections or []:
            if section and section.strip():
                sections.append(section.strip())

        return "\n\n".join(part.strip() for part in sections if part and part.strip())

    def _tool_result_to_biz_exception(self, result: ToolResult) -> BizException:
        error = result.error
        code_map = {
            "tool_input_invalid": ErrorCode.TOOL_INPUT_INVALID,
            "tool_timeout": ErrorCode.TOOL_TIMEOUT,
            "tool_output_invalid": ErrorCode.TOOL_OUTPUT_INVALID,
            "tool_execution_failed": ErrorCode.TOOL_EXECUTION_FAILED,
            "tool_unavailable": ErrorCode.TOOL_EXECUTION_FAILED,
        }

        error_code = code_map.get(
            error.error_code if error is not None else "",
            ErrorCode.TOOL_EXECUTION_FAILED,
        )

        return BizException(
            error_code,
            message=error.error_message if error is not None else "Tool 执行失败",
            data={
                "tool_name": result.tool_name,
                "trace_id": result.trace_id,
                "run_id": result.run_id,
                "error": error.model_dump() if error is not None else None,
            },
        )

    @abstractmethod
    async def _run(self, state: InterviewState) -> dict[str, Any] | OutputT:
        """核心逻辑，子类实现"""


def run_id_or_raise() -> str:
    from app.core.agent.observer import get_run_id

    run_id = get_run_id()
    if not run_id or run_id == "-":
        raise RuntimeError("current agent run_id is unavailable")
    return run_id
