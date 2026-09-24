"""安全相关工具：管理接口 Token 校验、比较字符串（常量时间比较）。"""

from __future__ import annotations

import hmac

from app.config import get_settings
from app.core.errors import ForbiddenError


def verify_admin_token(token: str | None) -> None:
    """校验管理接口 Token，不匹配时抛出 403。"""
    expected = get_settings().admin_token
    if not expected or not token or not hmac.compare_digest(str(token), str(expected)):
        raise ForbiddenError("Admin Token 无效")
