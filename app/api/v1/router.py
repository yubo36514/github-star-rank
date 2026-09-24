"""v1 路由聚合。

各子路由自带 prefix（如 /repos），此处只做挂载。
"""

from fastapi import APIRouter

from app.api.response import ok
from app.api.v1.endpoints import admin, favorites, languages, meta, repos

api_router = APIRouter()
api_router.include_router(repos.router)
api_router.include_router(languages.router)
api_router.include_router(favorites.router)
api_router.include_router(meta.router)
api_router.include_router(admin.router)


@api_router.get("/health", tags=["元数据"], summary="健康检查")
async def health() -> dict:
    """最简健康检查（不查库，供容器 HEALTHCHECK 使用）。"""
    return ok({"status": "ok"})
