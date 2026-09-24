"""FastAPI 依赖：数据库会话、客户端标识、管理鉴权。"""

from __future__ import annotations

import ipaddress
import logging

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import is_admin_token_valid, verify_admin_token
from app.db.session import get_db

logger = logging.getLogger(__name__)

# 收藏功能不使用登录体系，而是用浏览器 localStorage 中的随机 UUID 做隔离
CLIENT_ID_HEADER = "X-Client-Id"
ADMIN_TOKEN_HEADER = "X-Admin-Token"

# 允许「免 Token 放行」的回环地址（仅在 ADMIN_ALLOW_LOCAL=true 时生效）
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost"}


def _is_private_host(host: str) -> bool:
    """判断来源是否为内网地址（Docker 网关、局域网），供 ADMIN_ALLOW_PRIVATE 使用。"""
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:  # 域名等非 IP 形式
        return False


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    """数据库会话依赖（语义化别名）。"""
    return session


def get_client_id(x_client_id: str | None = Header(default=None, alias=CLIENT_ID_HEADER)) -> str:
    """读取客户端标识；为空时返回空串（此时收藏相关过滤不生效）。"""
    return (x_client_id or "").strip()


def require_admin(
    request: Request,
    x_admin_token: str | None = Header(default=None, alias=ADMIN_TOKEN_HEADER),
) -> str:
    """校验管理接口权限（优先级从上到下）：

    1. 请求头携带合法的 X-Admin-Token（脚本 / CI 的用法保持不变）
    2. 开启 ADMIN_ALLOW_LOCAL 且来源为回环地址时免 Token 放行（本机一键刷新）
    3. 其余情况统一返回 403
    """
    if is_admin_token_valid(x_admin_token):
        return x_admin_token or ""

    settings = get_settings()
    host = request.client.host if request.client else ""
    is_local = host in _LOOPBACK_HOSTS or (settings.admin_allow_private and _is_private_host(host))
    if settings.admin_allow_local and is_local:
        logger.warning(
            "管理接口本机放行（未携带 Token）: host=%s path=%s", host, request.url.path
        )
        return ""

    verify_admin_token(x_admin_token)  # Token 缺失或错误 -> 403
    return x_admin_token or ""
