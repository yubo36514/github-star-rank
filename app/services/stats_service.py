"""全局统计信息业务层（供页面头部展示）。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories import favorite_repo, meta_repo, repo_repo, snapshot_repo
from app.schemas import StatsOut


async def get_stats(session: AsyncSession) -> StatsOut:
    """汇总数据库与 Github 配额状态。"""
    meta = await meta_repo.all_meta(session)
    settings = get_settings()

    def to_int(value: str, default: int = -1) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    return StatsOut(
        repo_count=await repo_repo.count_repos(session),
        snapshot_count=await snapshot_repo.count_snapshots(session),
        favorite_count=await favorite_repo.count_all(session),
        last_fetch_at=meta.get("last_fetch_at", ""),
        last_fetch_status=meta.get("last_fetch_status", "never"),
        github_rate_remaining=to_int(meta.get("github_rate_remaining", "-1")),
        github_rate_limit=to_int(meta.get("github_rate_limit", "-1")),
        github_rate_reset_at=meta.get("github_rate_reset_at", ""),
        has_token=bool(settings.github_token),
    )
