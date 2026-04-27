"""
简历上传响应 DTO 定义。

创建时间: 2026-04-27
开发人: zcry
"""

# app/schemas/response/resume_upload.py

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResumeUploadResultDTO(BaseModel):
    """简历上传后的流程初始化结果"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    candidate_id: str = Field(..., description="候选人 ID")
    candidate_name: str = Field(..., description="候选人姓名")

    screening_passed: bool = Field(..., description="HR 初筛是否通过")
