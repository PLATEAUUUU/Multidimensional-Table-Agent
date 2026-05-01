# app/agents/manager/manager_agent.py
from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.interview_state import InterviewState


class ManagerAgent(BaseAgent):
    agent_name = "manager"
    allowed_tools = ["feishu_sync", "structured_hiring_recommendation"]
    output_model = None

    async def _run(self, state: InterviewState) -> dict[str, Any]:
        return {
            "current_step": "manager:awaiting_structured_decision",
            "route_decision": {
                "decision": "await_skill_result",
                "next_agent": "supervisor",
                "reason": "Placeholder result pending skill output.",
            },
            "messages": [],
            "token_usage": {"prompt": 0, "completion": 0, "total": 0},
        }
