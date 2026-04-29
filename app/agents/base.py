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
from time import perf_counter
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app.agents.interview_state import InterviewState
from app.core.errors import BizException, ErrorCode
from app.core.observer import AgentObserver
from app.core.security import ContentSafetyInterceptor, SecurityInterceptionError


OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseAgent(ABC, Generic[OutputT]):
    """
    Agent 运行时外壳（Harness）

    当前版本支持两种开发模式：

    1. 结构化输出模式
       - 子类声明 output_model
       - _run 返回 dict 或 Pydantic model
       - BaseAgent 负责 model_validate + 默认挂载 latest_agent_output

    2. 直接 patch 模式
       - 子类不声明 output_model
       - _run 直接返回 state patch(dict)
       - 适合当前 demo 快速开发
    """

    agent_name: str = ""
    allowed_tools: list[str] = []
    output_model: type[OutputT] | None = None

    def __init__(
        self,
        model_name: str,
        observer: AgentObserver,
        prompt_template: str,
        safety_interceptor: ContentSafetyInterceptor | None = None,
    ) -> None:
        if not self.agent_name:
            raise ValueError(f"{self.__class__.__name__} 必须定义 agent_name")

        self.model_name = model_name
        self.observer = observer
        self.prompt_template = prompt_template
        self.safety_interceptor = safety_interceptor or ContentSafetyInterceptor()
        self.logger = logging.getLogger(f"agent.{self.agent_name}")

    async def __call__(self, state: InterviewState) -> dict[str, Any]:
        """Agent 统一执行入口"""

        started_at = perf_counter()
        trace_id = self.observer.ensure_trace_id(state.get("trace_id"))
        run_id = uuid4().hex

        base_metadata = {
            "run_id": run_id,
            "candidate_id": state.get("candidate_id"),
            "current_round": str(state.get("current_round")),
            "process_status": str(state.get("process_status")),
            "active_agent": state.get("active_agent"),
        }

        # -------- 记录调用开始 --------
        self.observer.record_agent_call(
            agent_name=self.agent_name,
            trace_id=trace_id,
            metadata=base_metadata,
        )

        try:
            # -------- 输入安全 --------
            await self._preflight(state)

            # -------- 执行 Agent --------
            raw_output = await self._run(state)

            # -------- 输出归一化 / 结构校验 --------
            normalized_output = self._normalize_output(raw_output)

            # -------- 输出安全 --------
            await self._audit_output(normalized_output)

            # -------- 转换为 State Patch --------
            patch = self._to_state_patch(normalized_output)
            if not isinstance(patch, dict):
                raise TypeError(f"{self.agent_name}._to_state_patch 必须返回 dict[str, Any]")

            # -------- 注入运行信息 --------
            patch["trace_id"] = trace_id
            patch["run_id"] = run_id
            patch["active_agent"] = self.agent_name
            patch["is_safe"] = True

            patch["token_usage"] = self.observer.record_token_usage(
                self.agent_name,
                trace_id,
                patch.get("token_usage"),
            )

            duration_ms = int((perf_counter() - started_at) * 1000)

            # -------- 记录成功 --------
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
                ErrorCode.AGENT_EXECUTION_FAILED,
                message=f"{self.agent_name} 输出结构校验失败",
                data={"errors": exc.errors()},
            ) from exc

        except Exception as exc:
            duration_ms = int((perf_counter() - started_at) * 1000)

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
            raise BizException(
                ErrorCode.AGENT_EXECUTION_FAILED,
                message=f"{self.agent_name} 执行失败",
                data={
                    "agent_name": self.agent_name,
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            ) from exc

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
        """
        统一输出归一化：

        - 如果声明了 output_model，则强制做结构化校验
        - 如果没声明 output_model，则要求 _run 直接返回 dict patch
        """

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
        """
        默认行为：

        - 结构化输出模式：挂到 latest_agent_output
        - 直接 patch 模式：原样返回
        """

        if isinstance(output, BaseModel):
            return {
                "latest_agent_output": output,
            }

        return dict(output)

    @abstractmethod
    async def _run(self, state: InterviewState) -> dict[str, Any] | OutputT:
        """核心逻辑，子类实现"""
