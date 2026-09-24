"""收藏数据访问层。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite import Favorite


async def add_favorite(session: AsyncSession, client_id: str, repo_id: int) -> bool:
    """新增收藏，已存在则幂等返回 False（未新增）。"""
    exists = await session.scalar(
        select(Favorite.id).where(Favorite.client_id == client_id, Favorite.repo_id == repo_id)
    )
    if exists is not None:
        return False
    session.add(Favorite(client_id=client_id, repo_id=repo_id, created_at=datetime.utcnow()))
    await session.commit()
    return True


async def remove_favorite(session: AsyncSession, client_id: str, repo_id: int) -> bool:
    """取消收藏，返回是否真的删除了记录。"""
    result = await session.execute(
        delete(Favorite).where(Favorite.client_id == client_id, Favorite.repo_id == repo_id)
    )
    await session.commit()
    return (result.rowcount or 0) > 0


async def list_repo_ids(session: AsyncSession, client_id: str) -> list[int]:
    """查询某个客户端的全部收藏仓库 ID（按收藏时间倒序）。"""
    rows = (
        await session.execute(
            select(Favorite.repo_id)
            .where(Favorite.client_id == client_id)
            .order_by(Favorite.created_at.desc())
        )
    ).all()
    return [int(r[0]) for r in rows]


async def count_by_client(session: AsyncSession, client_id: str) -> int:
    """某个客户端的收藏数量。"""
    return int(
        await session.scalar(
            select(func.count(Favorite.id)).where(Favorite.client_id == client_id)
        )
        or 0
    )


async def count_all(session: AsyncSession) -> int:
    """全站收藏总数。"""
    return int(await session.scalar(select(func.count(Favorite.id))) or 0)
