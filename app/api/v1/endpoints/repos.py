"""榜单接口：列表（分页/筛选/排序/搜索）与详情。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_id, get_session
from app.api.response import ok
from app.core.errors import BadRequestError, NotFoundError
from app.services import ranking_service

router = APIRouter(prefix="/repos", tags=["榜单"])


@router.get("", summary="榜单列表")
async def list_repos(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    language: str | None = Query(None, description="编程语言，多个用逗号分隔，如 Python,Go"),
    keyword: str | None = Query(None, description="仓库名/描述关键词"),
    sort_by: str = Query("stars_7d", description="排序字段：stars_7d/total_stars/stars_7d_rate/created_at"),
    order: str = Query("desc", description="排序方向：desc 或 asc"),
    only_favorites: bool = Query(False, description="仅返回当前客户端收藏的项目"),
    session: AsyncSession = Depends(get_session),
    client_id: str = Depends(get_client_id),
) -> dict:
    """分页查询 7 日 Star 增量榜单。"""
    if order not in ("desc", "asc"):
        raise BadRequestError("order 只能是 desc 或 asc")

    languages = [item.strip() for item in language.split(",") if item.strip()] if language else None

    result = await ranking_service.list_repos(
        session,
        page=page,
        page_size=page_size,
        languages=languages,
        keyword=keyword,
        sort_by=sort_by,
        order=order,
        only_favorites=only_favorites,
        client_id=client_id or None,
    )
    return ok(result.model_dump())


@router.get("/{repo_id}", summary="项目详情")
async def get_repo(
    repo_id: int,
    session: AsyncSession = Depends(get_session),
    client_id: str = Depends(get_client_id),
) -> dict:
    """查询单个项目详情与近 8 天 Star 趋势。"""
    detail = await ranking_service.get_repo_detail(session, repo_id, client_id or None)
    if detail is None:
        raise NotFoundError("项目不存在")
    return ok(detail.model_dump())
