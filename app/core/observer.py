"""
Agent 执行路径追溯

创建时间：2026/4/29
开发人：zcry
"""
from __future__ import annotations

import contextvars
import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# ============================================================
# Trace ID 上下文
# ============================================================

_trace_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id",
    default="-",
)


def get_trace_id() -> str:
    """获取当前协程上下文中的 trace_id"""
    return _trace_id_context.get()


def set_trace_id(trace_id: str) -> contextvars.Token[str]:
    """设置 trace_id，并返回 context token，方便后续 reset"""
    return _trace_id_context.set(trace_id)


def reset_trace_id(token: contextvars.Token[str]) -> None:
    """恢复 trace_id 上下文"""
    _trace_id_context.reset(token)


class TraceIdFilter(logging.Filter):
    """把 trace_id 注入到每条日志里"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        return True


def configure_logging(level: str = "INFO") -> None:
    """
    初始化根日志配置

    说明：
    1. 只在 root logger 没有 handler 时自动加 handler
    2. 每条日志都会自动带上 trace_id
    """
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.addFilter(TraceIdFilter())
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | trace=%(trace_id)s | %(name)s | %(message)s"
            )
        )
        root_logger.addHandler(handler)

    root_logger.setLevel(level.upper())


# ============================================================
# Token 使用统计
# ============================================================

@dataclass(slots=True)
class TokenUsageSnapshot:
    """统一 token 统计结构"""

    prompt: int = 0
    completion: int = 0
    total: int = 0

    def merge(self, usage: Mapping[str, Any] | None) -> "TokenUsageSnapshot":
        """把外部 usage 合并进当前快照"""
        if not usage:
            return self

        self.prompt += int(usage.get("prompt", 0))
        self.completion += int(usage.get("completion", 0))
        self.total += int(usage.get("total", 0))
        return self

    def to_dict(self) -> dict[str, int]:
        """转成可序列化字典。"""
        return {
            "prompt": self.prompt,
            "completion": self.completion,
            "total": self.total,
        }


# ============================================================
# 观测器
# ============================================================

class AgentObserver:
    """
    统一的运行时观测入口

    当前职责：
    1. trace_id 管理
    2. Agent 生命周期记录
    3. Tool 调用生命周期记录
    4. token 使用统计
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------
    # Trace helpers
    # ------------------------------

    def new_trace_id(self) -> str:
        """生成新的 trace_id。"""
        trace_id = uuid.uuid4().hex
        self.logger.debug("Generated new trace id: %s", trace_id)
        return trace_id

    def ensure_trace_id(self, current_trace_id: str | None) -> str:
        """
        确保当前上下文存在 trace_id

        如果 state / request 已经带了 trace_id，则复用；
        否则自动生成新的 trace_id。
        """
        trace_id = current_trace_id or self.new_trace_id()
        set_trace_id(trace_id)
        return trace_id

    # ------------------------------
    # Generic event
    # ------------------------------

    def record_event(
        self,
        event_name: str,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        """记录通用事件"""
        self.logger.info(
            "observer_event=%s payload=%s",
            event_name,
            self._safe_dict(payload),
        )

    # ------------------------------
    # Agent lifecycle
    # ------------------------------

    def record_agent_call(
        self,
        agent_name: str,
        trace_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """
        记录 Agent 开始调用

        建议 metadata 至少包含：
        - run_id
        - candidate_id
        - current_round
        - process_status
        - active_agent
        """
        self.logger.info(
            "agent_call agent=%s trace_id=%s metadata=%s",
            agent_name,
            trace_id,
            self._safe_dict(metadata),
        )

    def record_agent_success(
        self,
        agent_name: str,
        trace_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """
        记录 Agent 成功结束

        建议 metadata 可包含：
        - run_id
        - duration_ms
        - output_type
        - decision
        - current_round
        """
        self.logger.info(
            "agent_success agent=%s trace_id=%s metadata=%s",
            agent_name,
            trace_id,
            self._safe_dict(metadata),
        )

    def record_agent_failure(
        self,
        agent_name: str,
        trace_id: str,
        error: Exception | str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """
        记录 Agent 失败

        error 支持传 Exception 或字符串
        metadata 建议包含：
        - run_id
        - duration_ms
        - candidate_id
        - current_round
        """
        if isinstance(error, Exception):
            error_type = error.__class__.__name__
            error_message = str(error)
        else:
            error_type = "Error"
            error_message = str(error)

        payload = {
            **self._safe_dict(metadata),
            "error_type": error_type,
            "error_message": error_message,
        }

        self.logger.error(
            "agent_failure agent=%s trace_id=%s payload=%s",
            agent_name,
            trace_id,
            payload,
        )

    # ------------------------------
    # Tool lifecycle
    # ------------------------------

    def record_tool_call(
        self,
        tool_name: str,
        trace_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """
        记录工具开始调用

        建议 metadata 可包含：
        - run_id
        - agent_name
        - arguments
        """
        self.logger.info(
            "tool_call tool=%s trace_id=%s metadata=%s",
            tool_name,
            trace_id,
            self._safe_dict(metadata),
        )

    def record_tool_result(
        self,
        tool_name: str,
        trace_id: str,
        success: bool,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """
        记录工具执行结果

        建议 metadata 可包含：
        - run_id
        - agent_name
        - duration_ms
        - result
        - error_message
        """
        level = logging.INFO if success else logging.ERROR
        self.logger.log(
            level,
            "tool_result tool=%s trace_id=%s success=%s metadata=%s",
            tool_name,
            trace_id,
            success,
            self._safe_dict(metadata),
        )

    # ------------------------------
    # Token usage
    # ------------------------------

    def record_token_usage(
        self,
        agent_name: str,
        trace_id: str,
        usage: Mapping[str, Any] | None,
    ) -> dict[str, int]:
        """
        统一记录 token 使用

        传入 None 时也会返回标准结构，避免上层判空。
        """
        snapshot = TokenUsageSnapshot().merge(usage)

        self.logger.info(
            "token_usage agent=%s trace_id=%s usage=%s",
            agent_name,
            trace_id,
            snapshot.to_dict(),
        )

        return snapshot.to_dict()

    # ------------------------------
    # Internal helpers
    # ------------------------------

    def _safe_dict(
        self,
        payload: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        """
        把 Mapping 转成普通 dict，避免日志里出现不可读对象

        这里只做浅转换，保持简单。
        """
        if not payload:
            return {}
        return dict(payload)


# ============================================================
# FastAPI / Starlette 中间件
# ============================================================

class TraceContextMiddleware(BaseHTTPMiddleware):
    """为每个 HTTP 请求注入 trace_id"""

    def __init__(self, app, observer: AgentObserver) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.observer = observer

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        trace_id = request.headers.get("x-trace-id") or self.observer.new_trace_id()
        token = set_trace_id(trace_id)
        request.state.trace_id = trace_id

        try:
            response: Response = await call_next(request)
            response.headers["x-trace-id"] = trace_id
            return response
        finally:
            reset_trace_id(token)
