"""
评估结果领域模型定义

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from __future__ import annotations

from typing import Union, Literal
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InterviewRoundType


class BaseEvaluationDetail(BaseModel):
    """面评详情基类"""
    model_config = ConfigDict(extra="forbid")


class HRScreeningDetail(BaseEvaluationDetail):
    round_type: Literal[InterviewRoundType.HR_SCREENING] = InterviewRoundType.HR_SCREENING
    education_match: str | None = Field(default=None, description="教育背景匹配情况")
    skill_match: str | None = Field(default=None, description="技能匹配情况")
    resume_risk_points: list[str] = Field(default_factory=list, description="简历风险点")
    screening_reason: str = Field(..., description="初筛理由")


class TechnicalEvaluationDetail(BaseEvaluationDetail):
    round_type: Literal[
        InterviewRoundType.TECHNICAL_1,
        InterviewRoundType.TECHNICAL_2,
    ]

    technical_score: float | None = Field(default=None, description="技术能力评分")
    project_score: float | None = Field(default=None, description="项目能力评分")
    coding_score: float | None = Field(default=None, description="编码能力评分")
    strengths: list[str] = Field(default_factory=list, description="优势")
    weaknesses: list[str] = Field(default_factory=list, description="不足")
    suggested_follow_up_questions: list[str] = Field(default_factory=list, description="建议追问点")


class ManagerEvaluationDetail(BaseEvaluationDetail):
    round_type: Literal[InterviewRoundType.MANAGER] = InterviewRoundType.MANAGER
    ownership_score: float | None = Field(default=None, description="责任心评分")
    communication_score: float | None = Field(default=None, description="沟通表达评分")
    teamwork_score: float | None = Field(default=None, description="团队协作评分")
    potential_comment: str | None = Field(default=None, description="发展潜力评价")


class HROfferEvaluationDetail(BaseEvaluationDetail):
    round_type: Literal[InterviewRoundType.HR_OFFER] = InterviewRoundType.HR_OFFER
    salary_expectation: str | None = Field(default=None, description="薪资期望")
    availability_date: str | None = Field(default=None, description="可入职时间")
    offer_risk_points: list[str] = Field(default_factory=list, description="录用风险点")
    negotiation_comment: str | None = Field(default=None, description="谈薪评价")


EvaluationDetail = Union[
    HRScreeningDetail,
    TechnicalEvaluationDetail,
    ManagerEvaluationDetail,
    HROfferEvaluationDetail,
]



class Evaluation(BaseModel):
    """轮次评估实体"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str | None = Field(default=None, description="内部主键")
    evaluation_id: str = Field(..., description="评估业务 ID")
    candidate_id: str = Field(..., description="候选人 ID")

    round_type: InterviewRoundType = Field(..., description="所属面试轮次")

    score: float | None = Field(default=None, description="综合评估分数")
    passed: bool = Field(..., description="是否通过该轮")
    summary: str = Field(..., description="评估摘要")
    detailed_comment: str = Field(..., description="详细评语")

    details: EvaluationDetail = Field(..., description="不同轮次的结构化面评详情")

    created_at: str = Field(..., description="评估创建时间，ISO 8601 字符串")
