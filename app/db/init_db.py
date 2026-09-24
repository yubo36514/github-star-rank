"""数据库初始化：建表 + 初始元数据。"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.config import get_settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models import ApiCache, Favorite, MetaInfo, Repo, RepoSnapshot, SchedulerLock  # noqa: F401

logger = logging.getLogger(__name__)

# 启动时写入的默认元数据
_DEFAULT_META = {
    "last_fetch_at": "",
    "last_fetch_status": "never",  # never / success / partial / failed
    "last_fetch_count": "0",
    "github_rate_remaining": "-1",
    "github_rate_limit": "-1",
    "github_rate_reset_at": "",
}


async def init_database() -> None:
    """创建所有表并写入默认元数据（幂等）。"""
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for key, value in _DEFAULT_META.items():
            exists = await session.scalar(select(MetaInfo).where(MetaInfo.key == key))
            if exists is None:
                session.add(MetaInfo(key=key, value=value))
        await session.commit()

    logger.info("数据库初始化完成: %s", settings.database_url)
