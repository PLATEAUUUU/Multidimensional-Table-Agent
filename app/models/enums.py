"""
系统状态与流程枚举定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BaseStrEnum(str, Enum):
    """字符串枚举基类"""

    def __str__(self) -> str:
        """返回枚举的字符串值，便于日志和序列化使用"""

        return self.value


class InterviewRoundType(BaseStrEnum):
    """面试轮次类型，也是轮次业务 ID"""

    HR_SCREENING = "hr_screening"
    TECHNICAL_1 = "technical_1"
    TECHNICAL_2 = "technical_2"
    MANAGER = "manager"
    HR_OFFER = "hr_offer"

    @property
    def display_name(self) -> str:
        return {
            InterviewRoundType.HR_SCREENING: "HR 初筛",
            InterviewRoundType.TECHNICAL_1: "技术一面",
            InterviewRoundType.TECHNICAL_2: "技术二面",
            InterviewRoundType.MANAGER: "主管面",
            InterviewRoundType.HR_OFFER: "HR 谈薪 / 录用",
        }[self]

    @property
    def order(self) -> int:
        return {
            InterviewRoundType.HR_SCREENING: 1,
            InterviewRoundType.TECHNICAL_1: 2,
            InterviewRoundType.TECHNICAL_2: 3,
            InterviewRoundType.MANAGER: 4,
            InterviewRoundType.HR_OFFER: 5,
        }[self]


class InterviewRoundStatus(BaseStrEnum):
    """面试轮次状态枚举"""

    LOCKED = "LOCKED"
    AVAILABLE = "AVAILABLE"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"

    @property
    def display_text(self) -> str:
        """返回前端展示所需的中文状态文本。"""

        return {
            InterviewRoundStatus.LOCKED: "未解锁",
            InterviewRoundStatus.AVAILABLE: "可进入",
            InterviewRoundStatus.IN_PROGRESS: "进行中",
            InterviewRoundStatus.PASSED: "已通过",
            InterviewRoundStatus.FAILED: "未通过",
            InterviewRoundStatus.FINISHED: "已完成",
            InterviewRoundStatus.CANCELLED: "已取消",
        }[self]

    @property
    def is_clickable(self) -> bool:
        """返回当前轮次在前端是否允许点击进入或查看历史。"""

        return self in {
            InterviewRoundStatus.AVAILABLE,
            InterviewRoundStatus.IN_PROGRESS,
            InterviewRoundStatus.PASSED,
            InterviewRoundStatus.FAILED,
            InterviewRoundStatus.FINISHED,
        }

    @property
    def is_terminal(self) -> bool:
        """返回当前轮次是否已经进入终态"""

        return self in {
            InterviewRoundStatus.PASSED,
            InterviewRoundStatus.FAILED,
            InterviewRoundStatus.FINISHED,
            InterviewRoundStatus.CANCELLED,
        }


class CandidateProcessStatus(BaseStrEnum):
    """候选人整体流程状态枚举"""

    RESUME_UPLOADED = "RESUME_UPLOADED"
    HR_SCREENING = "HR_SCREENING"
    HR_REJECTED = "HR_REJECTED"
    INTERVIEWING = "INTERVIEWING"
    ROUND_IN_PROGRESS = "ROUND_IN_PROGRESS"
    ROUND_FAILED = "ROUND_FAILED"
    OFFER_PENDING = "OFFER_PENDING"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    REJECTED = "REJECTED"
    FINISHED = "FINISHED"

    @property
    def display_text(self) -> str:
        """返回候选人流程状态对应的前端展示文案"""

        return {
            CandidateProcessStatus.RESUME_UPLOADED: "简历已上传，正在处理中",
            CandidateProcessStatus.HR_SCREENING: "HR 初筛中",
            CandidateProcessStatus.HR_REJECTED: "未通过初筛，流程已结束",
            CandidateProcessStatus.INTERVIEWING: "面试流程进行中",
            CandidateProcessStatus.ROUND_IN_PROGRESS: "当前轮面试进行中",
            CandidateProcessStatus.ROUND_FAILED: "本轮未通过，流程已结束",
            CandidateProcessStatus.OFFER_PENDING: "进入 HR 谈薪 / 录用阶段",
            CandidateProcessStatus.OFFER_ACCEPTED: "已录用",
            CandidateProcessStatus.REJECTED: "流程已结束",
            CandidateProcessStatus.FINISHED: "流程正常结束",
        }[self]

    @property
    def is_terminal(self) -> bool:
        """返回候选人整体流程是否已结束。"""

        return self in {
            CandidateProcessStatus.HR_REJECTED,
            CandidateProcessStatus.ROUND_FAILED,
            CandidateProcessStatus.OFFER_ACCEPTED,
            CandidateProcessStatus.REJECTED,
            CandidateProcessStatus.FINISHED,
        }


__all__ = [
    "BaseStrEnum",
    "InterviewRoundStatus",
    "InterviewRoundType",
    "CandidateProcessStatus",
    "RECOMMENDED_INTERVIEW_ROUNDS",
]

