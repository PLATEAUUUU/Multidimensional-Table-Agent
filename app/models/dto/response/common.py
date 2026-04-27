"""
通用响应 DTO 定义

创建时间: 2026-04-27
开发人: zcry
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一的接口响应包装模型"""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    # code 为 0 表示成功，非 0 可由上层约定错误码
    code: int = Field(default=0, description="业务状态码。")
    message: str = Field(default="success", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")
    trace_id: str = Field(..., description="请求链路追踪 ID")

