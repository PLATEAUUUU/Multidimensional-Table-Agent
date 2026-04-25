from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from app.agents.hr_agent import HrAgent
from app.agents.manager_agent import ManagerAgent
from app.agents.state import InterviewState
from app.agents.supervisor import SupervisorAgent
from app.agents.tech_agent import TechAgent
from app.config import AppSettings
from app.core.observer import AgentObserver
from app.core.security import ContentSafetyInterceptor
from app.memory.bitable_checkpointer import BitableCheckpointer
from app.tools.mcp.feishu_tool import FeishuTool


def build_interview_graph(
    settings: AppSettings,
    observer: AgentObserver,
    feishu_tool: FeishuTool,
) -> Callable:
    """
    Build a deterministic LangGraph topology.

    Routing decisions are constrained by `route_decision.next_agent`
    and never delegated to free-form LLM text.
    """

    safety_interceptor = ContentSafetyInterceptor()
    checkpointer = BitableCheckpointer(observer=observer, feishu_tool=feishu_tool)

    graph = StateGraph(InterviewState)
    supervisor = SupervisorAgent(
        model_name=settings.default_model_name,
        observer=observer,
        prompt_template=settings.load_prompt(settings.supervisor_prompt_path),
        safety_interceptor=safety_interceptor,
    )
    hr = HrAgent(
        model_name=settings.default_model_name,
        observer=observer,
        prompt_template=settings.load_prompt(settings.hr_prompt_path),
        safety_interceptor=safety_interceptor,
    )
    tech = TechAgent(
        model_name=settings.default_model_name,
        observer=observer,
        prompt_template=settings.load_prompt(settings.tech_prompt_path),
        safety_interceptor=safety_interceptor,
    )
    manager = ManagerAgent(
        model_name=settings.default_model_name,
        observer=observer,
        prompt_template=settings.load_prompt(settings.manager_prompt_path),
        safety_interceptor=safety_interceptor,
    )

    async def persist_state(state: InterviewState) -> dict:
        await feishu_tool.atomic_sync_session(
            session_id=state["session_id"],
            state_payload=state,
        )
        return {"last_checkpoint_id": state["session_id"]}

    graph.add_node("supervisor", supervisor)
    graph.add_node("hr", hr)
    graph.add_node("tech", tech)
    graph.add_node("manager", manager)
    graph.add_node("persist_state", persist_state)
    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "persist_state")
    graph.add_edge("hr", "persist_state")
    graph.add_edge("tech", "persist_state")
    graph.add_edge("manager", "persist_state")

    def route_after_persist(state: InterviewState) -> str:
        active_agent = state.get("active_agent")
        next_agent = state.get("route_decision", {}).get("next_agent", "end")
        if active_agent == "supervisor":
            return next_agent if next_agent in {"hr", "tech", "manager"} else END
        return "supervisor" if next_agent == "supervisor" else END

    graph.add_conditional_edges("persist_state", route_after_persist)

    return graph.compile(checkpointer=checkpointer)
