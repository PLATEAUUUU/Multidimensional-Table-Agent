from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import RoundStatus


class TechAgent(BaseAgent):
    agent_name = "tech"
    allowed_tools = ["feishu_sync", "structured_skill_evaluation"]

    async def execute(self, state) -> dict[str, Any]:  # type: ignore[override]
        return {
            "current_step": "tech:awaiting_structured_decision",
            "round_status": state.get("round_status", RoundStatus.TECH),
            "route_decision": {
                "decision": "await_skill_result",
                "next_agent": "supervisor",
                "reason": "Placeholder result pending skill output.",
            },
            "messages": [],
            "token_usage": {"prompt": 0, "completion": 0, "total": 0},
        }

