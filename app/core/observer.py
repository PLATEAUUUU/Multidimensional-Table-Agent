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


_trace_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


def get_trace_id() -> str:
    return _trace_id_context.get()


def set_trace_id(trace_id: str) -> contextvars.Token[str]:
    return _trace_id_context.set(trace_id)


def reset_trace_id(token: contextvars.Token[str]) -> None:
    _trace_id_context.reset(token)


class TraceIdFilter(logging.Filter):
    """Inject trace identifiers into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        return True


def configure_logging(level: str = "INFO") -> None:
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


@dataclass(slots=True)
class TokenUsageSnapshot:
    prompt: int = 0
    completion: int = 0
    total: int = 0

    def merge(self, usage: Mapping[str, Any] | None) -> "TokenUsageSnapshot":
        if not usage:
            return self
        self.prompt += int(usage.get("prompt", 0))
        self.completion += int(usage.get("completion", 0))
        self.total += int(usage.get("total", 0))
        return self

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt": self.prompt,
            "completion": self.completion,
            "total": self.total,
        }


class AgentObserver:
    """Single place for audit events, token accounting, and trace helpers."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def new_trace_id(self) -> str:
        trace_id = uuid.uuid4().hex
        self.logger.debug("Generated new trace id: %s", trace_id)
        return trace_id

    def ensure_trace_id(self, current_trace_id: str | None) -> str:
        trace_id = current_trace_id or self.new_trace_id()
        set_trace_id(trace_id)
        return trace_id

    def record_event(self, event_name: str, payload: Mapping[str, Any] | None = None) -> None:
        self.logger.info("observer_event=%s payload=%s", event_name, dict(payload or {}))

    def record_agent_call(self, agent_name: str, trace_id: str, metadata: Mapping[str, Any] | None = None) -> None:
        self.logger.info(
            "agent_call agent=%s trace_id=%s metadata=%s",
            agent_name,
            trace_id,
            dict(metadata or {}),
        )

    def record_token_usage(self, agent_name: str, trace_id: str, usage: Mapping[str, Any] | None) -> dict[str, int]:
        snapshot = TokenUsageSnapshot().merge(usage)
        self.logger.info(
            "token_usage agent=%s trace_id=%s usage=%s",
            agent_name,
            trace_id,
            snapshot.to_dict(),
        )
        return snapshot.to_dict()


class TraceContextMiddleware(BaseHTTPMiddleware):
    """Attach a trace id to every incoming HTTP request."""

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

