
# app/graphs/state/interview_state.py

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import NotRequired, Required

from app.models.domain.candidate import Candidate
from app.models.domain.resume import Resume
from app.models.domain.interview_round import InterviewRound
from app.models.domain.interviewer import Interviewer
from app.models.domain.evaluation import Evaluation
from app.models.domain.chat_message import ChatMessage
from app.models.enums import CandidateProcessStatus, InterviewRoundType
from app.schemas.agent.round_output import (
    ResumeParseOutput,
    HRScreeningOutput,
    InterviewRoundOutput,
)

class TokenUsage(TypedDict):
    """LLM token 使用统计"""
    prompt: int
    completion: int
    total: int


class InterviewState(TypedDict, total=False):
    """招聘面试 LangGraph 全局状态"""

    # -------- identity --------
    candidate_id: Required[str]
    trace_id: Required[str]

    # -------- domain context --------
    candidate: NotRequired[Candidate]
    resume: NotRequired[Resume]

    rounds: NotRequired[dict[InterviewRoundType, InterviewRound]]
    interviewers: NotRequired[dict[InterviewRoundType, Interviewer]]
    evaluations: NotRequired[dict[InterviewRoundType, Evaluation]]

    # -------- conversation --------
    messages: Required[Annotated[list[BaseMessage], add_messages]]
    chat_messages: NotRequired[list[ChatMessage]]

    # -------- process control --------
    current_round: Required[InterviewRoundType]
    process_status: Required[CandidateProcessStatus]
    process_finished: Required[bool]

    # -------- agent node outputs --------
    resume_parse_output: NotRequired[ResumeParseOutput]
    hr_screening_output: NotRequired[HRScreeningOutput]
    latest_round_output: NotRequired[InterviewRoundOutput]
    round_outputs: NotRequired[dict[InterviewRoundType, InterviewRoundOutput]]

    # -------- engineering / audit --------
    token_usage: Required[TokenUsage]
    is_safe: Required[bool]

    # -------- persistence --------
    last_checkpoint_id: NotRequired[str]
    bitable_record_ids: NotRequired[dict[str, str]]
    idempotency_key: NotRequired[str]
    error_message: NotRequired[str]


def default_token_usage() -> TokenUsage:
    return {"prompt": 0, "completion": 0, "total": 0}


def build_initial_state(
    candidate_id: str,
    trace_id: str,
) -> InterviewState:
    """构造初始 State"""

    return InterviewState(
        candidate_id=candidate_id,
        trace_id=trace_id,
        messages=[],
        chat_messages=[],
        current_round=InterviewRoundType.HR_SCREENING,
        process_status=CandidateProcessStatus.RESUME_UPLOADED,
        process_finished=False,
        evaluations={},
        round_outputs={},
        token_usage=default_token_usage(),
        is_safe=True,
        active_agent="resume_parser",
        bitable_record_ids={},
    )