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
from pathlib import Path
from threading import RLock
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# ============================================================
# Trace / Run 上下文
# ============================================================

_trace_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id",
    default="-",
)
_run_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "run_id",
    default="-",
)

_DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | trace=%(trace_id)s | run=%(run_id)s | %(name)s | %(message)s"
)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TRACE_LOG_DIR = _PROJECT_ROOT / "data" / "log"


def get_trace_id() -> str:
    """获取当前协程上下文中的 trace_id"""
    return _trace_id_context.get()


def set_trace_id(trace_id: str) -> contextvars.Token[str]:
    """设置 trace_id，并返回 context token，方便后续 reset"""
    return _trace_id_context.set(trace_id)


def reset_trace_id(token: contextvars.Token[str]) -> None:
    """恢复 trace_id 上下文"""
    _trace_id_context.reset(token)


def get_run_id() -> str:
    """获取当前协程上下文中的 run_id"""
    return _run_id_context.get()


def set_run_id(run_id: str) -> contextvars.Token[str]:
    """设置 run_id，并返回 context token，方便后续 reset"""
    return _run_id_context.set(run_id)


def reset_run_id(token: contextvars.Token[str]) -> None:
    """恢复 run_id 上下文"""
    _run_id_context.reset(token)


class TraceIdFilter(logging.Filter):
    """把 trace_id / run_id 注入到每条日志里"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        record.run_id = get_run_id()
        return True


class PerTraceFileRouterHandler(logging.Handler):
    """
    按 trace_id 自动分流日志到文件

    设计目标：
    1. 一条完整业务链路共享同一个 trace_id
    2. 同一条链路中的多个 agent / tool 日志统一写入同一个文件
    3. 文件名使用最大层级标识：data/log/<trace_id>.log
    4. 没有 trace_id 的日志只打印控制台，不落盘
    """

    def __init__(self, log_dir: Path) -> None:
        super().__init__()
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._handlers_by_trace_id: dict[str, logging.Handler] = {}
        self._lock = RLock()

    def emit(self, record: logging.LogRecord) -> None:
        trace_id = getattr(record, "trace_id", None)
        if not trace_id or trace_id == "-":
            return

        try:
            handler = self._get_or_create_handler(str(trace_id))
            handler.emit(record)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        with self._lock:
            for handler in self._handlers_by_trace_id.values():
                handler.close()
            self._handlers_by_trace_id.clear()
        super().close()

    def _get_or_create_handler(self, trace_id: str) -> logging.Handler:
        with self._lock:
            handler = self._handlers_by_trace_id.get(trace_id)
            if handler is not None:
                return handler

            file_path = self.log_dir / f"{trace_id}.log"
            handler = logging.FileHandler(file_path, encoding="utf-8")
            handler.setLevel(self.level)

            # 复用 router 的 formatter / filters，保证控制台和文件格式一致
            if self.formatter is not None:
                handler.setFormatter(self.formatter)
            for current_filter in self.filters:
                handler.addFilter(current_filter)

            self._handlers_by_trace_id[trace_id] = handler
            return handler


def configure_logging(level: str = "INFO") -> None:
    """
    初始化根日志配置

    说明：
    1. 每条日志自动带 trace_id / run_id
    2. 控制台日志保留
    3. 有 trace_id 的日志会自动落盘到 data/log/<trace_id>.log
    """
    root_logger = logging.getLogger()
    level_value = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(fmt=_DEFAULT_LOG_FORMAT)

    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level_value)
        console_handler.addFilter(TraceIdFilter())
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        trace_file_handler = PerTraceFileRouterHandler(_TRACE_LOG_DIR)
        trace_file_handler.setLevel(level_value)
        trace_file_handler.addFilter(TraceIdFilter())
        trace_file_handler.setFormatter(formatter)
        root_logger.addHandler(trace_file_handler)

    root_logger.setLevel(level_value)


# ============================================================
# Token 使用统计
# ============================================================

@dataclass(slots=True)
class TokenUsageSnapshot:
    """统一 token 统计结构。"""

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
        """转成可序列化字典"""
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
        """生成新的 """
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
        self._sync_trace_context_from_payload(payload)
        self._sync_run_context(payload)

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
        self._sync_trace_context(trace_id)
        self._sync_run_context(metadata)

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
        self._sync_trace_context(trace_id)
        self._sync_run_context(metadata)

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

        error 支持传 Exception 或字符串。
        metadata 建议包含：
        - run_id
        - duration_ms
        - candidate_id
        - current_round
        """
        self._sync_trace_context(trace_id)
        self._sync_run_context(metadata)

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
        self._sync_trace_context(trace_id)
        self._sync_run_context(metadata)

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
        self._sync_trace_context(trace_id)
        self._sync_run_context(metadata)

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

        传入 None 时也会返回标准结构，避免上层判空
        """
        self._sync_trace_context(trace_id)

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
        """把 Mapping 转成普通 dict，避免日志里出现不可读对象"""
        if not payload:
            return {}
        return dict(payload)

    def _sync_trace_context(self, trace_id: str | None) -> None:
        """
        同步 trace_id 到当前协程上下文

        这样同一条业务链路里的任意 logger 都会自动写入同一个 trace 日志文件
        """
        if isinstance(trace_id, str) and trace_id.strip():
            set_trace_id(trace_id.strip())

    def _sync_trace_context_from_payload(
        self,
        payload: Mapping[str, Any] | None,
    ) -> None:
        """从 payload 中提取 trace_id 并同步到上下文。"""
        if not payload:
            return

        trace_id = payload.get("trace_id")
        if isinstance(trace_id, str) and trace_id.strip():
            set_trace_id(trace_id.strip())

    def _sync_run_context(self, metadata: Mapping[str, Any] | None) -> None:
        """
        如果 metadata 里带了 run_id，就同步到当前协程上下文

        这样同一个 trace 文件中的日志还能继续区分具体是哪次 agent 执行
        """
        if not metadata:
            return

        run_id = metadata.get("run_id")
        if isinstance(run_id, str) and run_id.strip():
            set_run_id(run_id.strip())


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
        trace_token = set_trace_id(trace_id)
        run_token = set_run_id("-")
        request.state.trace_id = trace_id

        try:
            response: Response = await call_next(request)
            response.headers["x-trace-id"] = trace_id
            return response
        finally:
            reset_run_id(run_token)
            reset_trace_id(trace_token)
