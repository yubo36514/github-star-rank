"""统一响应封装与全局异常处理。

所有接口返回：
{
  "code": 0,
  "message": "ok",
  "timestamp": 1758604800,
  "data": {...}
}
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import BusinessError

logger = logging.getLogger(__name__)


def ok(data: Any = None, message: str = "ok", code: int = 0) -> dict[str, Any]:
    """构造成功响应体。"""
    return {
        "code": code,
        "message": message,
        "timestamp": int(time.time()),
        "data": data,
    }


def fail(message: str, code: int = 50001, http_status: int = 500) -> JSONResponse:
    """构造失败响应（HTTP 响应对象）。"""
    return JSONResponse(
        status_code=http_status,
        content={
            "code": code,
            "message": message,
            "timestamp": int(time.time()),
            "data": None,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，保证前端始终收到统一结构。"""

    @app.exception_handler(BusinessError)
    async def _business_handler(_request: Request, exc: Exception) -> JSONResponse:
        business_exc: BusinessError = exc  # type: ignore[assignment]
        logger.warning("业务异常: code=%s msg=%s", business_exc.code, business_exc.message)
        return fail(business_exc.message, code=business_exc.code, http_status=business_exc.http_status)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return fail(f"参数校验失败: {exc.errors()}", code=40001, http_status=400)

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return fail(str(exc.detail), code=40000 + exc.status_code, http_status=exc.status_code)

    @app.exception_handler(Exception)
    async def _server_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未处理异常: %s", exc)
        return fail("服务内部错误，请查看服务端日志", code=50001, http_status=500)
