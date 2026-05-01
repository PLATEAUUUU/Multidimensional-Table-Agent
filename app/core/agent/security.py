"""
安全拦截：输入输出安全校验

创建时间：2026/4/29
开发人：zcry
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any


class SecurityInterceptionError(RuntimeError):
    """安全拦截异常"""


class ContentSafetyInterceptor:
    """Agent 输入输出安全检查器"""

    SENSITIVE_KEYS = {
        "app_token",
        "table_id",
        "record_id",
        "secret",
        "access_token",
        "refresh_token",
        "api_key",
        "password",
    }

    DANGEROUS_PATTERNS = [
        r"ignore\s+previous\s+instructions",
        r"忽略.*(系统|之前|上面).*指令",
        r"泄露.*(prompt|提示词|密钥|token)",
        r"删除.*(全部|所有)",
        r"rm\s+-rf",
        r"drop\s+table",
    ]

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    async def preflight_agent_input(
        self,
        agent_name: str,
        payload: Mapping[str, Any],
    ) -> bool:
        """Agent 输入安全检查"""

        text = self._flatten_payload(payload)

        if self._contains_dangerous_text(text):
            self.logger.warning("Agent input blocked: agent=%s", agent_name)
            return False

        return True

    async def audit_agent_output(
        self,
        agent_name: str,
        payload: Mapping[str, Any],
    ) -> bool:
        """Agent 输出安全检查"""

        text = self._flatten_payload(payload)

        if self._contains_sensitive_key(payload):
            self.logger.warning("Agent output blocked by sensitive key: agent=%s", agent_name)
            return False

        if self._contains_dangerous_text(text):
            self.logger.warning("Agent output blocked by dangerous text: agent=%s", agent_name)
            return False

        return True

    async def validate_skill_invocation(
        self,
        skill_name: str,
        agent_name: str,
        allowed_skills: list[str] | None = None,
    ) -> bool:
        """校验 Agent 是否允许调用指定 Skill"""

        if allowed_skills is None:
            return True

        allowed = skill_name in allowed_skills

        if not allowed:
            self.logger.warning(
                "Skill invocation blocked: agent=%s skill=%s allowed=%s",
                agent_name,
                skill_name,
                allowed_skills,
            )

        return allowed

    def _contains_dangerous_text(self, text: str) -> bool:
        lowered = text.lower()

        return any(
            re.search(pattern, lowered, flags=re.IGNORECASE)
            for pattern in self.DANGEROUS_PATTERNS
        )

    def _contains_sensitive_key(self, payload: Mapping[str, Any]) -> bool:
        for key, value in payload.items():
            if key.lower() in self.SENSITIVE_KEYS:
                return True

            if isinstance(value, Mapping) and self._contains_sensitive_key(value):
                return True

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, Mapping) and self._contains_sensitive_key(item):
                        return True

        return False

    def _flatten_payload(self, payload: Any) -> str:
        """把嵌套对象转成可检查文本"""

        if payload is None:
            return ""

        if isinstance(payload, str):
            return payload

        if isinstance(payload, Mapping):
            return " ".join(
                f"{key} {self._flatten_payload(value)}"
                for key, value in payload.items()
            )

        if isinstance(payload, list | tuple | set):
            return " ".join(self._flatten_payload(item) for item in payload)

        return str(payload)

