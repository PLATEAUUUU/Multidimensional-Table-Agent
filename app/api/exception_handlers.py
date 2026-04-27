# app/api/exception_handlers.py

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import BizException, ErrorCode
from app.core.response import error_response, generate_trace_id


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""

    @app.exception_handler(BizException)
    async def handle_biz_exception(
        request: Request,
        exc: BizException,
    ) -> JSONResponse:
        trace_id = _get_trace_id(request)

        body = error_response(
            code=exc.code,
            message=exc.message,
            data=exc.data,
            trace_id=trace_id,
        )

        return JSONResponse(
            status_code=exc.http_status,
            content=body.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        trace_id = _get_trace_id(request)

        body = error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="请求参数校验失败",
            data={"errors": exc.errors()},
            trace_id=trace_id,
        )

        return JSONResponse(
            status_code=422,
            content=body.model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unknown_exception(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        trace_id = _get_trace_id(request)

        body = error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="服务端内部错误",
            data=None,
            trace_id=trace_id,
        )

        return JSONResponse(
            status_code=500,
            content=body.model_dump(),
        )


def _get_trace_id(request: Request) -> str:
    """优先复用请求头中的 trace id，没有则生成新的"""

    return request.headers.get("X-Trace-Id") or generate_trace_id()