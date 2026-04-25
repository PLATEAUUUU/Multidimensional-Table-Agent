from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import RoundStatus


class SupervisorAgent(BaseAgent):
    agent_name = "supervisor"
    allowed_tools = ["route_round", "persist_state"]

    async def execute(self, state) -> dict[str, Any]:  # type: ignore[override]
        round_status = RoundStatus(state.get("round_status", RoundStatus.INIT))
        route_map = {
            RoundStatus.INIT: {"decision": "route", "next_agent": "hr"},
            RoundStatus.HR: {"decision": "route", "next_agent": "hr"},
            RoundStatus.TECH: {"decision": "route", "next_agent": "tech"},
            RoundStatus.MANAGER: {"decision": "route", "next_agent": "manager"},
            RoundStatus.COMPLETED: {"decision": "finish", "next_agent": "end"},
            RoundStatus.REJECTED: {"decision": "finish", "next_agent": "end"},
        }
        return {
            "current_step": f"supervisor:{round_status.value}",
            "route_decision": route_map[round_status],
            "round_status": round_status,
            "messages": [],
            "token_usage": {"prompt": 0, "completion": 0, "total": 0},
        }

