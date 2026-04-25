from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import RoundStatus


class ManagerAgent(BaseAgent):
    agent_name = "manager"
    allowed_tools = ["feishu_sync", "structured_hiring_recommendation"]

    async def execute(self, state) -> dict[str, Any]:  # type: ignore[override]
        return {
            "current_step": "manager:awaiting_structured_decision",
            "round_status": state.get("round_status", RoundStatus.MANAGER),
            "route_decision": {
                "decision": "await_skill_result",
                "next_agent": "supervisor",
                "reason": "Placeholder result pending skill output.",
            },
            "messages": [],
            "token_usage": {"prompt": 0, "completion": 0, "total": 0},
        }

