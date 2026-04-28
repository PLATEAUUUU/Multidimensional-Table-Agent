
# app/graphs/state/interview_state.py
"""
LangGraph State 状态图

创建时间：2026/4/28
开发人：zcry
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from typing_extensions import NotRequired, Required

from app.models.domain.candidate import Candidate
from app.models.domain.resume import Resume
from app.models.domain.interview_round import InterviewRound
from app.models.domain.interviewer import Interviewer
from app.models.domain.evaluation import Evaluation
from app.models.enums import CandidateProcessStatus, InterviewRoundType
from app.schemas.agent.base_agent_output import BaseAgentOutput

class TokenUsage(TypedDict):
    """LLM token 使用统计"""
    prompt: int
    completion: int
    total: int


class InterviewState(TypedDict, total=False):
    """招聘面试 LangGraph 全局状态，聊天记录为 SubGraph 私有"""

    # -------- identity --------
    candidate_id: Required[str]
    trace_id: Required[str]

    # -------- domain context --------
    candidate: NotRequired[Candidate]
    resume: NotRequired[Resume]

    # 每一轮状态
    rounds: NotRequired[InterviewRound]
    # 面试官信息
    interviewers: NotRequired[dict[InterviewRoundType, Interviewer]]
    # 面评结果
    evaluations: NotRequired[dict[InterviewRoundType, Evaluation]]

    # -------- process control --------
    current_round: Required[InterviewRoundType]
    process_status: Required[CandidateProcessStatus]
    process_finished: Required[bool]

    # -------- agent node outputs --------
    # 最近一次 Agent 输出，不区分具体类型
    latest_agent_output: NotRequired[BaseAgentOutput]
    # 每个 Agent 最近一次输出，不共享子图内部历史，只保留最终输出快照
    agent_outputs: NotRequired[dict[str, BaseAgentOutput]]

    # -------- engineering / audit --------
    token_usage: Required[TokenUsage]
    is_safe: Required[bool]

    # 运行时信息
    active_agent: NotRequired[str]

    # -------- persistence --------
    last_checkpoint_id: NotRequired[str]
    bitable_record_ids: NotRequired[dict[str, str]]
    idempotency_key: NotRequired[str]
    error_message: NotRequired[str]


def default_token_usage() -> TokenUsage:
    """初始化的token统计"""
    return {"prompt": 0, "completion": 0, "total": 0}


def build_initial_state(
    candidate_id: str,
    trace_id: str,
) -> InterviewState:
    """构造初始 State"""

    return InterviewState(
        candidate_id=candidate_id,
        trace_id=trace_id,
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