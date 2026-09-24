"""收藏业务层。"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.repositories import favorite_repo, repo_repo

logger = logging.getLogger(__name__)


async def add_favorite(session: AsyncSession, client_id: str, repo_id: int) -> dict:
    """新增收藏（幂等）：已收藏时不会重复插入。"""
    repo = await repo_repo.get_by_repo_id(session, repo_id)
    if repo is None:
        raise NotFoundError("项目不存在")

    await favorite_repo.add_favorite(session, client_id, repo_id)
    count = await favorite_repo.count_by_client(session, client_id)
    return {"repo_id": repo_id, "is_favorite": True, "favorite_count": count}


async def remove_favorite(session: AsyncSession, client_id: str, repo_id: int) -> dict:
    """取消收藏（幂等）。"""
    await favorite_repo.remove_favorite(session, client_id, repo_id)
    count = await favorite_repo.count_by_client(session, client_id)
    return {"repo_id": repo_id, "is_favorite": False, "favorite_count": count}


async def list_favorite_ids(session: AsyncSession, client_id: str) -> list[int]:
    """查询某客户端的全部收藏 ID。"""
    return await favorite_repo.list_repo_ids(session, client_id)
