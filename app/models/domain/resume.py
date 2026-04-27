"""
简历领域模型定义
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

class EducationItem(BaseModel):
    school: str | None = Field(default=None, description="学校名称")
    degree: str | None = Field(default=None, description="学位，如本科/硕士/博士")
    major: str | None = Field(default=None, description="专业")
    time_range: str | None = Field(default=None, description="时间范围，如 2019-2023")


class ExperienceItem(BaseModel):
    start_time: str | None = Field(default=None, description="开始时间")
    end_time: str | None = Field(default=None, description="结束时间")
    title: str | None = Field(default=None, description="经历名称")
    company : str | None = Field(default=None, description="公司名称")
    summary: str | None = Field(default=None, description="经历概述")
    responsibility: str | None = Field(default=None, description="个人职责")
    

class Resume(BaseModel):
    """简历领域实体"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str | None = Field(default=None, description="内部主键")
    resume_id: str = Field(..., description="简历业务唯一标识")
    candidate_id: str = Field(..., description="所属候选人 ID")
    
    # 原始信息
    file_path: str | None = Field(default=None, description="原始文件存储路径")
    
    # 解析后的结构化字段
    name: str | None = Field(default=None, description="姓名")
    phone: str | None = Field(default=None, description="电话")
    email: str | None = Field(default=None, description="邮箱")
    educations: list[EducationItem] = Field(default_factory=list,description="教育经历")

    work_experience: list[ExperienceItem] | None = Field(default_factory=list, description="工作/实习经历")
    project_experience: list[ExperienceItem] | None = Field(default_factory=list, description="项目经历")
    skills: list[str] | None = Field(default=None, description="技能关键词")
    
    # 完整结构化数据
    extra_fields: dict[str, Any] | None = Field(
        default=None,
        description="简历解析模块返回的其他字段",
    )
    
    # 元信息
    source: str | None = Field(default=None, description="简历来源，如 campus_recruitment")
    created_at: str | None = Field(default=None, description="简历上传时间")