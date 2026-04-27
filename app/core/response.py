# app/core/response.py

from __future__ import annotations

from uuid import uuid4
from typing import Generic, TypeVar
from app.core.errors import ErrorCode
from app.models.dto.response.common import ApiResponse


T = TypeVar("T")


def generate_trace_id() -> str:
    """生成请求链路追踪 ID"""

    return uuid4().hex


def success_response(
    data: T | None = None,
    message: str = "success",
    trace_id: str | None = None,
) -> ApiResponse[T]:
    """构造成功响应"""

    return ApiResponse[T](
        code=ErrorCode.SUCCESS.value,
        message=message,
        data=data,
        trace_id=trace_id or generate_trace_id(),
    )


def error_response(
    code: ErrorCode,
    message: str,
    data: dict | None = None,
    trace_id: str | None = None,
) -> ApiResponse[dict]:
    """构造失败响应"""

    return ApiResponse[dict](
        code=code.value,
        message=message,
        data=data,
        trace_id=trace_id or generate_trace_id(),
    )