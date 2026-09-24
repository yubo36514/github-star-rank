"""元数据 / 缓存 / 调度锁的数据访问层。"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta import ApiCache, MetaInfo, SchedulerLock

logger = logging.getLogger(__name__)


# ------------------------- MetaInfo -------------------------
async def get_meta(session: AsyncSession, key: str, default: str = "") -> str:
    """读取元数据，不存在时返回默认值。"""
    value = await session.scalar(select(MetaInfo.value).where(MetaInfo.key == key))
    return value if value is not None else default


async def set_meta(session: AsyncSession, key: str, value: str) -> None:
    """写入元数据（存在则更新）。"""
    obj = await session.scalar(select(MetaInfo).where(MetaInfo.key == key))
    if obj is None:
        session.add(MetaInfo(key=key, value=value))
    else:
        obj.value = value
    await session.commit()


async def set_meta_batch(session: AsyncSession, items: dict[str, str]) -> None:
    """批量写入元数据。"""
    for key, value in items.items():
        obj = await session.scalar(select(MetaInfo).where(MetaInfo.key == key))
        if obj is None:
            session.add(MetaInfo(key=key, value=value))
        else:
            obj.value = value
    await session.commit()


async def all_meta(session: AsyncSession) -> dict[str, str]:
    """返回全部元数据字典。"""
    rows = (await session.execute(select(MetaInfo))).scalars().all()
    return {row.key: row.value or "" for row in rows}


# ------------------------- ApiCache -------------------------
async def cache_get(session: AsyncSession, key: str) -> Any | None:
    """读取缓存，过期或不存在返回 None。"""
    now_ts = int(time.time())
    row = await session.scalar(
        select(ApiCache).where(ApiCache.cache_key == key, ApiCache.expires_at > now_ts)
    )
    if row is None:
        return None
    try:
        return json.loads(row.payload)
    except json.JSONDecodeError:  # 缓存损坏时当作未命中
        return None


async def cache_set(session: AsyncSession, key: str, payload: Any, ttl: int) -> None:
    """写入缓存（ttl 秒；ttl <= 0 表示不缓存）。"""
    if ttl <= 0:
        return
    row = await session.scalar(select(ApiCache).where(ApiCache.cache_key == key))
    data = json.dumps(payload, ensure_ascii=False)
    expires = int(time.time()) + ttl
    if row is None:
        session.add(ApiCache(cache_key=key, payload=data, expires_at=expires))
    else:
        row.payload = data
        row.expires_at = expires
    await session.commit()


async def cache_cleanup(session: AsyncSession) -> int:
    """清理已过期缓存，返回删除条数。"""
    result = await session.execute(delete(ApiCache).where(ApiCache.expires_at < int(time.time())))
    await session.commit()
    return result.rowcount or 0


# ------------------------- SchedulerLock -------------------------
async def try_acquire_lock(session: AsyncSession, task_name: str, ttl_seconds: int = 3600) -> bool:
    """尝试获取任务锁：锁不存在或已过期才算获取成功。"""
    now = datetime.utcnow()
    lock = await session.scalar(select(SchedulerLock).where(SchedulerLock.task_name == task_name))
    if lock is None:
        session.add(
            SchedulerLock(task_name=task_name, locked_at=now, expires_at=now + timedelta(seconds=ttl_seconds))
        )
        await session.commit()
        return True
    if lock.expires_at and lock.expires_at < now:
        lock.locked_at = now
        lock.expires_at = now + timedelta(seconds=ttl_seconds)
        await session.commit()
        return True
    return False


async def release_lock(session: AsyncSession, task_name: str) -> None:
    """释放任务锁（直接删除记录）。"""
    await session.execute(delete(SchedulerLock).where(SchedulerLock.task_name == task_name))
    await session.commit()
