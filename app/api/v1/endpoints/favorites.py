"""收藏接口：新增 / 取消 / 列表 / ID 集合。

收藏不依赖登录体系，用请求头 X-Client-Id（浏览器 localStorage 中的 UUID）区分用户。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_id, get_session
from app.api.response import ok
from app.core.errors import BadRequestError
from app.services import favorite_service, ranking_service

router = APIRouter(prefix="/favorites", tags=["收藏"])


class FavoriteCreate(BaseModel):
    """新增收藏请求体。"""

    repo_id: int


def _require_client_id(client_id: str) -> str:
    """收藏操作必须携带客户端标识。"""
    if not client_id:
        raise BadRequestError("缺少 X-Client-Id 请求头")
    return client_id


@router.get("/ids", summary="收藏 ID 集合")
async def favorite_ids(
    session: AsyncSession = Depends(get_session),
    client_id: str = Depends(get_client_id),
) -> dict:
    """返回当前客户端收藏的仓库 ID 列表（用于批量点亮卡片星标）。"""
    if not client_id:
        return ok([])
    return ok(await favorite_service.list_favorite_ids(session, client_id))


@router.get("", summary="收藏列表")
async def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("stars_7d"),
    order: str = Query("desc"),
    session: AsyncSession = Depends(get_session),
    client_id: str = Depends(get_client_id),
) -> dict:
    """分页返回当前客户端收藏的项目（结构与榜单列表一致）。"""
    _require_client_id(client_id)
    result = await ranking_service.list_repos(
        session,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        order=order,
        only_favorites=True,
        client_id=client_id,
    )
    return ok(result.model_dump())


@router.post("", summary="新增收藏")
async def create_favorite(
    payload: FavoriteCreate,
    session: AsyncSession = Depends(get_session),
    client_id: str = Depends(get_client_id),
) -> dict:
    """收藏一个项目（重复收藏幂等返回成功）。"""
    _require_client_id(client_id)
    result = await favorite_service.add_favorite(session, client_id, payload.repo_id)
    return ok(result)


@router.delete("/{repo_id}", summary="取消收藏")
async def delete_favorite(
    repo_id: int,
    session: AsyncSession = Depends(get_session),
    client_id: str = Depends(get_client_id),
) -> dict:
    """取消收藏（未收藏时幂等返回成功）。"""
    _require_client_id(client_id)
    result = await favorite_service.remove_favorite(session, client_id, repo_id)
    return ok(result)
