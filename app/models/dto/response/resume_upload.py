"""
简历上传响应 DTO 定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ...enums import CandidateProcessStatus


class ResumeUploadResultDTO(BaseModel):
    """简历上传后的流程初始化结果。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    candidate_id: str = Field(..., description="候选人 ID。")
    candidate_name: str = Field(..., description="候选人姓名。")
    screening_passed: bool = Field(..., description="初筛是否通过。")
    process_status: CandidateProcessStatus = Field(..., description="当前整体流程状态。")
    current_round: str | None = Field(default=None, description="当前已进入的轮次 ID。")
    process_finished: bool = Field(..., description="流程是否已经结束。")

