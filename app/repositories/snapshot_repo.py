"""快照数据访问层。"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import RepoSnapshot


async def upsert_snapshot(
    session: AsyncSession,
    *,
    repo_id: int,
    snapshot_date: str,
    total_stars: int,
    forks_count: int = 0,
    open_issues_count: int = 0,
    delta_stars: int = 0,
) -> None:
    """写入一条快照；同一仓库同一天重复写入时更新（幂等）。"""
    stmt = insert(RepoSnapshot).values(
        repo_id=repo_id,
        snapshot_date=snapshot_date,
        total_stars=total_stars,
        forks_count=forks_count,
        open_issues_count=open_issues_count,
        delta_stars=delta_stars,
        fetched_at=datetime.utcnow(),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["repo_id", "snapshot_date"],
        set_={
            "total_stars": stmt.excluded.total_stars,
            "forks_count": stmt.excluded.forks_count,
            "open_issues_count": stmt.excluded.open_issues_count,
            "delta_stars": stmt.excluded.delta_stars,
            "fetched_at": stmt.excluded.fetched_at,
        },
    )
    await session.execute(stmt)


async def latest_snapshot(session: AsyncSession, repo_id: int) -> RepoSnapshot | None:
    """查询某个仓库最新的一条快照。"""
    return (
        (
            await session.execute(
                select(RepoSnapshot)
                .where(RepoSnapshot.repo_id == repo_id)
                .order_by(RepoSnapshot.snapshot_date.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )


async def snapshot_on_or_before(
    session: AsyncSession, repo_id: int, target_date: str
) -> RepoSnapshot | None:
    """查询不晚于 target_date 的最近一条快照（用于取 7 日基线）。"""
    return (
        (
            await session.execute(
                select(RepoSnapshot)
                .where(RepoSnapshot.repo_id == repo_id, RepoSnapshot.snapshot_date <= target_date)
                .order_by(RepoSnapshot.snapshot_date.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )


async def earliest_snapshot(session: AsyncSession, repo_id: int) -> RepoSnapshot | None:
    """查询某个仓库最早的一条快照。"""
    return (
        (
            await session.execute(
                select(RepoSnapshot)
                .where(RepoSnapshot.repo_id == repo_id)
                .order_by(RepoSnapshot.snapshot_date.asc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )


async def recent_snapshots(session: AsyncSession, repo_id: int, days: int = 8) -> list[RepoSnapshot]:
    """查询某个仓库最近 N 条快照（按日期升序，用于画趋势图）。"""
    rows = (
        (
            await session.execute(
                select(RepoSnapshot)
                .where(RepoSnapshot.repo_id == repo_id)
                .order_by(RepoSnapshot.snapshot_date.desc())
                .limit(days)
            )
        )
        .scalars()
        .all()
    )
    return list(reversed(rows))


async def count_snapshots(session: AsyncSession) -> int:
    """快照总数。"""
    from sqlalchemy import func

    return int(await session.scalar(select(func.count(RepoSnapshot.id))) or 0)


async def delete_snapshots_before(session: AsyncSession, date_str: str) -> int:
    """删除指定日期之前的快照，返回删除条数。"""
    result = await session.execute(
        delete(RepoSnapshot).where(RepoSnapshot.snapshot_date < date_str)
    )
    await session.commit()
    return result.rowcount or 0


async def repo_ids_with_snapshot_on(session: AsyncSession, date_str: str) -> set[int]:
    """查询在指定日期已有快照的仓库 ID 集合。"""
    rows = (
        await session.execute(
            select(RepoSnapshot.repo_id).where(RepoSnapshot.snapshot_date == date_str)
        )
    ).all()
    return {int(r[0]) for r in rows}


async def bulk_upsert(
    session: AsyncSession, rows: Iterable[dict], commit_every: int = 200
) -> int:
    """批量写入快照，按 commit_every 分批提交，返回写入条数。"""
    count = 0
    for row in rows:
        await upsert_snapshot(session, **row)
        count += 1
        if count % commit_every == 0:
            await session.commit()
    await session.commit()
    return count
