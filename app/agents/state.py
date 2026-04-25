from __future__ import annotations

from enum import Enum
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from typing_extensions import NotRequired, Required


class RoundStatus(str, Enum):
    INIT = "init"
    HR = "hr"
    TECH = "tech"
    MANAGER = "manager"
    COMPLETED = "completed"
    REJECTED = "rejected"


class TokenUsage(TypedDict):
    prompt: int
    completion: int
    total: int


class RouteDecision(TypedDict, total=False):
    decision: str
    next_agent: str
    reason: str


class InterviewState(TypedDict, total=False):
    # Business data
    session_id: Required[str]
    candidate_id: Required[str]
    messages: Required[Annotated[list[dict], add_messages]]

    # Engineering audit data
    trace_id: Required[str]
    token_usage: Required[TokenUsage]
    current_step: Required[str]
    is_safe: Required[bool]

    # Structured routing data
    round_status: NotRequired[RoundStatus]
    route_decision: NotRequired[RouteDecision]
    active_agent: NotRequired[str]
    last_checkpoint_id: NotRequired[str]


def default_token_usage() -> TokenUsage:
    return {"prompt": 0, "completion": 0, "total": 0}


def build_initial_state(session_id: str, candidate_id: str, trace_id: str) -> InterviewState:
    return InterviewState(
        session_id=session_id,
        candidate_id=candidate_id,
        messages=[],
        trace_id=trace_id,
        token_usage=default_token_usage(),
        current_step=RoundStatus.INIT.value,
        is_safe=True,
        round_status=RoundStatus.INIT,
        route_decision={"decision": "bootstrap", "next_agent": "supervisor"},
        active_agent="supervisor",
    )

