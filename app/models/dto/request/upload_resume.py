"""
上传简历请求 DTO 定义。

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UploadResumeRequest(BaseModel):
    """上传简历时附带的表单元数据。"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    # 这里仅描述 multipart/form-data 中与文件配套的表单字段。
    file_name: str = Field(..., description="上传文件名称")
    target_position: str = Field(..., description="候选人投递的目标岗位")
    source: str = Field(..., description="简历来源渠道，例如 campus 或 referral")

