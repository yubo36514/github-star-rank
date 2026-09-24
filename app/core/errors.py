"""统一业务异常与错误码。"""

from __future__ import annotations


class BusinessError(Exception):
    """业务异常基类：携带业务错误码与 HTTP 状态码。"""

    code = 50001
    http_status = 500
    message = "服务内部错误"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


class BadRequestError(BusinessError):
    code = 40001
    http_status = 400
    message = "参数校验失败"


class NotFoundError(BusinessError):
    code = 40401
    http_status = 404
    message = "资源不存在"


class ForbiddenError(BusinessError):
    code = 40301
    http_status = 403
    message = "无权限访问"


class GithubRateLimitError(BusinessError):
    """Github API 配额不足。"""

    code = 42901
    http_status = 429
    message = "Github API 配额不足，请稍后重试"
