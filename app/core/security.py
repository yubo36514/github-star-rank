"""安全相关工具：管理接口 Token 校验、比较字符串（常量时间比较）。"""

from __future__ import annotations

import hmac

from app.config import get_settings
from app.core.errors import ForbiddenError


def is_admin_token_valid(token: str | None) -> bool:
    """判断管理 Token 是否合法（不抛异常，供多分支鉴权使用）。"""
    expected = get_settings().admin_token
    if not expected or not token:
        return False
    return hmac.compare_digest(str(token), str(expected))


def verify_admin_token(token: str | None) -> None:
    """校验管理接口 Token，不匹配时抛出 403。"""
    if not is_admin_token_valid(token):
        raise ForbiddenError("Admin Token 无效")
