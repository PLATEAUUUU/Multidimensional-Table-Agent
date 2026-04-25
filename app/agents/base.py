from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from app.core.observer import AgentObserver
from app.core.security import ContentSafetyInterceptor, SecurityInterceptionError

if TYPE_CHECKING:
    from app.agents.state import InterviewState


class BaseAgent(ABC):
    """
    Shared agent contract.

    1. Prompt templates are loaded from config or external files.
    2. All invocations pass through security and observability hooks.
    3. Concrete agents only provide structured outputs, never side effects.
    """

    agent_name: str
    allowed_tools: list[str]

    def __init__(
        self,
        model_name: str,
        observer: AgentObserver,
        prompt_template: str,
        safety_interceptor: ContentSafetyInterceptor | None = None,
    ) -> None:
        self.model_name = model_name
        self.observer = observer
        self.prompt_template = prompt_template
        self.safety_interceptor = safety_interceptor or ContentSafetyInterceptor()
        self.logger = logging.getLogger(f"agent.{self.agent_name}")

    @abstractmethod
    async def execute(self, state: "InterviewState") -> dict[str, Any]:
        """Implement structured decision making without embedding business logic."""

    async def __call__(self, state: "InterviewState") -> dict[str, Any]:
        trace_id = self.observer.ensure_trace_id(state.get("trace_id"))
        state["trace_id"] = trace_id

        allowed = await self.safety_interceptor.preflight_agent_input(self.agent_name, state)
        if not allowed:
            raise SecurityInterceptionError(f"Input rejected for agent {self.agent_name}")

        self.observer.record_agent_call(
            self.agent_name,
            trace_id,
            metadata={
                "session_id": state.get("session_id"),
                "current_step": state.get("current_step"),
            },
        )
        self.logger.info("Invoking agent=%s model=%s", self.agent_name, self.model_name)

        result = await self.execute(state)
        result.setdefault("active_agent", self.agent_name)

        output_allowed = await self.safety_interceptor.audit_agent_output(self.agent_name, result)
        if not output_allowed:
            raise SecurityInterceptionError(f"Output rejected for agent {self.agent_name}")

        result["trace_id"] = trace_id
        result["is_safe"] = True
        result["token_usage"] = self.observer.record_token_usage(
            self.agent_name,
            trace_id,
            result.get("token_usage"),
        )
        return result

