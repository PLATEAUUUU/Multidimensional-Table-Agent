"""
Tool 工具调用失败错误类型

创建时间：2026/4/28
开发人：zcry
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

class ToolError(Exception):
    """
    所有工具异常的基类

    设计目标：
    1. 为 runtime 提供统一可识别的异常类型
    2. 保留 tool_name / error_code / details 等结构化信息
    3. 方便后续落日志、转 ToolResult、转 API 错误
    """

    default_error_code = "tool_error"

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        error_code: str | None = None,
        details: Mapping[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.error_code = error_code or self.default_error_code
        self.details = dict(details or {})
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """转为结构化错误载荷，方便写日志或塞进 ToolResult"""
        payload: dict[str, Any] = {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "error_message": self.message
        }

        if self.tool_name:
            payload["tool_name"] = self.tool_name

        if self.details:
            payload["details"] = self.details

        if self.cause:
            payload["cause_type"] = self.cause.__class__.__name__
            payload["cause_message"] = str(self.cause)

        return payload

    def with_tool_name(self, tool_name: str) -> "ToolError":
        """允许 runtime 在归一化后补齐 tool_name"""
        self.tool_name = tool_name
        return self


class ToolInputError(ToolError):
    """
    工具输入不合法，例如：
    - 缺少必填参数
    - 参数类型不对
    - 值超出允许范围
    """

    default_error_code = "tool_input_invalid"


class ToolUnavailableError(ToolError):
    """工具当前不可用，例如配置缺失、依赖未安装、外部服务未启用"""

    default_error_code = "tool_unavailable"


class ToolExecutionError(ToolError):
    """工具实际执行失败，例如第三方接口异常、命令执行失败"""

    default_error_code = "tool_execution_failed"


class ToolTimeoutError(ToolError):
    """工具调用超时"""

    default_error_code = "tool_timeout"


class ToolOutputValidationError(ToolError):
    """工具执行成功，但输出结构不符合预期"""

    default_error_code = "tool_output_invalid"


def normalize_tool_error(
    err: Exception,
    *,
    tool_name: str | None = None,
) -> ToolError:
    """
    把任意异常归一化为 ToolError，方便 runtime 统一处理

    映射规则：
    1. 已经是 ToolError -> 原样返回
    2. asyncio.TimeoutError -> ToolTimeoutError
    3. pydantic.ValidationError -> ToolInputError
    4. ValueError / TypeError -> ToolInputError
    5. 其他异常 -> ToolExecutionError
    """
    if isinstance(err, ToolError):
        if tool_name and not err.tool_name:
            err.with_tool_name(tool_name)
        return err

    if isinstance(err, asyncio.TimeoutError):
        return ToolTimeoutError(
            "Tool execution timed out",
            tool_name=tool_name,
            cause=err,
        )

    if isinstance(err, ValidationError):
        return ToolInputError(
            "Tool input validation failed",
            tool_name=tool_name,
            details={"errors": err.errors()},
            cause=err,
        )

    if isinstance(err, (ValueError, TypeError)):
        return ToolInputError(
            str(err) or "Invalid tool input",
            tool_name=tool_name,
            cause=err,
        )

    return ToolExecutionError(
        str(err) or "Tool execution failed",
        tool_name=tool_name,
        cause=err,
    )
