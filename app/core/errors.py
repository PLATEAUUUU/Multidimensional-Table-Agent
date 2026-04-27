from enum import IntEnum


class ErrorCode(IntEnum):
    SUCCESS = 0

    RESUME_UPLOAD_FAILED = 40001
    RESUME_PARSE_FAILED = 40002
    HR_SCREENING_FAILED = 40003

    CANDIDATE_NOT_FOUND = 40004
    ROUND_NOT_FOUND = 40005

    ROUND_LOCKED = 40006
    PREVIOUS_ROUND_NOT_FINISHED = 40007

    SESSION_NOT_FOUND = 40008

    AGENT_EXECUTION_FAILED = 40009
    FEISHU_TOOL_FAILED = 40010
    LARK_CLI_ERROR = 40011

    PROCESS_FINISHED = 40012

    EMPTY_MESSAGE = 40013
    ROUND_ALREADY_FINISHED = 40014

    AGENT_TIMEOUT = 40015

    FILE_FORMAT_NOT_SUPPORTED = 40016
    FILE_TOO_LARGE = 40017

    INTERNAL_ERROR = 50000


ERROR_META = {
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
    ErrorCode.FEISHU_TOOL_FAILED: (502, "FeishuCliTool 执行失败"),
    ErrorCode.LARK_CLI_ERROR: (502, "lark-cli 返回错误"),

    ErrorCode.PROCESS_FINISHED: (409, "流程已结束"),

    ErrorCode.EMPTY_MESSAGE: (400, "消息内容不能为空"),
    ErrorCode.ROUND_ALREADY_FINISHED: (409, "当前轮次已结束"),

    ErrorCode.AGENT_TIMEOUT: (504, "Agent 响应超时"),

    ErrorCode.FILE_FORMAT_NOT_SUPPORTED: (400, "仅支持 PDF / Word"),
    ErrorCode.FILE_TOO_LARGE: (413, "文件过大"),

    ErrorCode.INTERNAL_ERROR: (500, "服务端内部错误"),
}


class BizException(Exception):
    def __init__(self, code: ErrorCode, message: str | None = None):
        self.code = code

        http_status, default_msg = ERROR_META.get(
            code, (500, "unknown error")
        )

        self.http_status = http_status
        self.message = message or default_msg

        super().__init__(self.message)