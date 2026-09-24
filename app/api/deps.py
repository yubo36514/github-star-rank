"""FastAPI 依赖：数据库会话、客户端标识、管理鉴权。"""

from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_admin_token
from app.db.session import get_db

# 收藏功能不使用登录体系，而是用浏览器 localStorage 中的随机 UUID 做隔离
CLIENT_ID_HEADER = "X-Client-Id"
ADMIN_TOKEN_HEADER = "X-Admin-Token"


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    """数据库会话依赖（语义化别名）。"""
    return session


def get_client_id(x_client_id: str | None = Header(default=None, alias=CLIENT_ID_HEADER)) -> str:
    """读取客户端标识；为空时返回空串（此时收藏相关过滤不生效）。"""
    return (x_client_id or "").strip()


def require_admin(x_admin_token: str | None = Header(default=None, alias=ADMIN_TOKEN_HEADER)) -> str:
    """校验管理接口 Token。"""
    verify_admin_token(x_admin_token)
    return x_admin_token or ""
