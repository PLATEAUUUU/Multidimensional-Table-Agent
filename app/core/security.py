from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any


class SecurityInterceptionError(RuntimeError):
    """Raised when a request does not pass the configured guardrails."""


class ContentSafetyInterceptor:
    """
    Placeholder guardrails module.

    Real implementations should perform:
    1. Input moderation before any LLM invocation.
    2. Output moderation before responses are persisted or returned.
    3. Structured audit logging for rejected requests.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    async def preflight_agent_input(self, agent_name: str, payload: Mapping[str, Any]) -> bool:
        self.logger.info("preflight_agent_input agent=%s payload_keys=%s", agent_name, list(payload.keys()))
        return True

    async def audit_agent_output(self, agent_name: str, payload: Mapping[str, Any]) -> bool:
        self.logger.info("audit_agent_output agent=%s payload_keys=%s", agent_name, list(payload.keys()))
        return True

    async def validate_skill_invocation(self, skill_name: str, agent_name: str) -> bool:
        self.logger.info("validate_skill_invocation skill=%s agent=%s", skill_name, agent_name)
        return True

