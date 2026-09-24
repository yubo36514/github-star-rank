"""接口层：依赖、响应封装与 v1 路由。"""

from app.api.response import fail, ok, register_exception_handlers
from app.api.v1.router import api_router

__all__ = ["api_router", "ok", "fail", "register_exception_handlers"]
