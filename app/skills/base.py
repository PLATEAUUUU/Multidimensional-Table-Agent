from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.observer import AgentObserver
from app.core.security import ContentSafetyInterceptor, SecurityInterceptionError


class SkillInput(BaseModel):
    """All skills use Pydantic validation."""

    model_config = ConfigDict(extra="forbid")


class BaseSkill(ABC):
    name: str
    description: str
    allowed_agents: list[str] = ["*"]

    def __init__(
        self,
        observer: AgentObserver | None = None,
        safety_interceptor: ContentSafetyInterceptor | None = None,
    ) -> None:
        self.observer = observer or AgentObserver()
        self.safety_interceptor = safety_interceptor or ContentSafetyInterceptor()
        self.logger = logging.getLogger(f"skill.{self.name}")

    def _is_agent_allowed(self, agent_name: str) -> bool:
        return "*" in self.allowed_agents or agent_name in self.allowed_agents

    async def __call__(self, input_data: SkillInput, *, caller_agent: str) -> dict[str, Any]:
        if not self._is_agent_allowed(caller_agent):
            raise SecurityInterceptionError(f"Agent {caller_agent} is not allowed to use skill {self.name}")

        allowed = await self.safety_interceptor.validate_skill_invocation(self.name, caller_agent)
        if not allowed:
            raise SecurityInterceptionError(f"Skill invocation rejected for {self.name}")

        self.observer.record_event(
            "skill_invocation_started",
            {"skill": self.name, "caller_agent": caller_agent},
        )
        self.logger.info("Invoking skill=%s caller_agent=%s", self.name, caller_agent)

        result = await self.run(input_data)
        self.observer.record_event(
            "skill_invocation_completed",
            {"skill": self.name, "caller_agent": caller_agent},
        )
        return result

    @abstractmethod
    async def run(self, input_data: SkillInput) -> dict[str, Any]:
        """
        1. Validate caller permissions.
        2. Execute an atomic action.
        3. Provide structured outputs for deterministic routing.
        """

