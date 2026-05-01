"""
错误码定义

创建时间：2024/4/28
开发人：zcry
"""
from enum import IntEnum
from typing import Any
# app/core/errors.py

from __future__ import annotations

from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    """业务错误码"""

    SUCCESS = 0

    # -------- Resume --------
    RESUME_UPLOAD_FAILED = 40001
    RESUME_PARSE_FAILED = 40002
    HR_SCREENING_FAILED = 40003

    # -------- Domain / Process --------
    CANDIDATE_NOT_FOUND = 40004
    ROUND_NOT_FOUND = 40005
    ROUND_LOCKED = 40006
    PREVIOUS_ROUND_NOT_FINISHED = 40007
    SESSION_NOT_FOUND = 40008

    # -------- Agent --------
    AGENT_EXECUTION_FAILED = 40009
    AGENT_OUTPUT_VALIDATION_FAILED = 40018
    AGENT_SECURITY_BLOCKED = 40019
    AGENT_TIMEOUT = 40015

    # -------- Tool / Feishu CLI --------
    FEISHU_TOOL_FAILED = 40010
    LARK_CLI_ERROR = 40011
    TOOL_INPUT_INVALID = 40020
    TOOL_EXECUTION_FAILED = 40021
    TOOL_TIMEOUT = 40022
    TOOL_OUTPUT_INVALID = 40023

    # -------- Process Constraint --------
    PROCESS_FINISHED = 40012
    EMPTY_MESSAGE = 40013
    ROUND_ALREADY_FINISHED = 40014

    # -------- File --------
    FILE_FORMAT_NOT_SUPPORTED = 40016
    FILE_TOO_LARGE = 40017

    # -------- System --------
    INTERNAL_ERROR = 50000


ERROR_META: dict[ErrorCode, tuple[int, str]] = {
    ErrorCode.SUCCESS: (200, "success"),

    ErrorCode.RESUME_UPLOAD_FAILED: (400, "简历上传失败"),
    ErrorCode.RESUME_PARSE_FAILED: (400, "简历解析失败"),
    ErrorCode.HR_SCREENING_FAILED: (502, "HR Agent 初筛失败"),

    ErrorCode.CANDIDATE_NOT_FOUND: (404, "候选人不存在"),
    ErrorCode.ROUND_NOT_FOUND: (404, "面试轮次不存在"),
    ErrorCode.ROUND_LOCKED: (409, "当前轮次未解锁，无法进入"),
    ErrorCode.PREVIOUS_ROUND_NOT_FINISHED: (409, "上一轮尚未结束"),
    ErrorCode.SESSION_NOT_FOUND: (404, "聊天会话不存在"),

    ErrorCode.AGENT_EXECUTION_FAILED: (502, "Agent 执行失败"),
    ErrorCode.AGENT_OUTPUT_VALIDATION_FAILED: (500, "Agent 输出结构校验失败"),
    ErrorCode.AGENT_SECURITY_BLOCKED: (403, "Agent 输入或输出被安全策略拦截"),
    ErrorCode.AGENT_TIMEOUT: (504, "Agent 响应超时"),

    ErrorCode.FEISHU_TOOL_FAILED: (502, "FeishuCliTool 执行失败"),
    ErrorCode.LARK_CLI_ERROR: (502, "lark-cli 返回错误"),
    ErrorCode.TOOL_INPUT_INVALID: (400, "Tool 输入参数非法"),
    ErrorCode.TOOL_EXECUTION_FAILED: (502, "Tool 执行失败"),
    ErrorCode.TOOL_TIMEOUT: (504, "Tool 执行超时"),
    ErrorCode.TOOL_OUTPUT_INVALID: (502, "Tool 输出结果非法"),

    ErrorCode.PROCESS_FINISHED: (409, "流程已结束"),
    ErrorCode.EMPTY_MESSAGE: (400, "消息内容不能为空"),
    ErrorCode.ROUND_ALREADY_FINISHED: (409, "当前轮次已结束"),

    ErrorCode.FILE_FORMAT_NOT_SUPPORTED: (400, "仅支持 PDF / Word"),
    ErrorCode.FILE_TOO_LARGE: (413, "文件过大"),

    ErrorCode.INTERNAL_ERROR: (500, "服务端内部错误"),
}


class BizException(Exception):
    """业务异常"""

    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.code = code

        http_status, default_msg = ERROR_META.get(
            code,
            ERROR_META[ErrorCode.INTERNAL_ERROR],
        )

        self.http_status = http_status
        self.message = message or default_msg
        self.data = data

        super().__init__(self.message)