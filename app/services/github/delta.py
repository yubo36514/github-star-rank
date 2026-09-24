"""7 日 Star 增量计算。

规则（见 PRD 附录 B）：
- stars_7d = 当前快照 Star 数 - 7 天前（或之前最近一条）快照 Star 数
- 历史不足 7 天时，取最早快照作为基线，并标记 is_partial=True
- 差值为负（取消 Star / 仓库重建）时取 0
"""

from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import RepoSnapshot
from app.repositories import repo_repo, snapshot_repo
from app.utils.number_util import safe_rate
from app.utils.time_util import days_ago_str, today_str, utc_now

logger = logging.getLogger(__name__)


def _pick_base(snapshots: list[RepoSnapshot], target_date: str) -> tuple[RepoSnapshot | None, bool]:
    """从按日期升序的快照列表中挑选基线快照。

    :return: (基线快照, 是否估算值)
    """
    if not snapshots:
        return None, False
    candidate: RepoSnapshot | None = None
    for snap in snapshots:  # 升序：最后一个 <= target_date 的即为基线
        if snap.snapshot_date <= target_date:
            candidate = snap
        else:
            break
    if candidate is not None:
        return candidate, False
    # 历史不足 7 天：用最早的一条兜底，标记为估算值
    return snapshots[0], True


async def compute_deltas(session: AsyncSession) -> int:
    """计算所有跟踪中仓库的 1 日 / 7 日 Star 增量，返回更新数量。"""
    today = today_str()
    base_7d_date = days_ago_str(7)
    base_1d_date = days_ago_str(1)

    repos = await repo_repo.list_active_repos(session)
    if not repos:
        logger.info("没有需要计算增量的仓库")
        return 0

    # 一次性加载近 9 天快照，避免逐仓库查询产生大量 SQL
    cutoff = days_ago_str(9)
    rows = (
        (await session.execute(select(RepoSnapshot).where(RepoSnapshot.snapshot_date >= cutoff)))
        .scalars()
        .all()
    )
    grouped: dict[int, list[RepoSnapshot]] = defaultdict(list)
    for snap in rows:
        grouped[snap.repo_id].append(snap)
    for snaps in grouped.values():
        snaps.sort(key=lambda s: s.snapshot_date)

    updated = 0
    now = utc_now()
    for repo in repos:
        snaps = grouped.get(repo.repo_id)
        if not snaps:
            continue

        current = snaps[-1]
        # 只处理「今天已有快照」的仓库，避免用旧数据覆盖指标
        if current.snapshot_date < today:
            continue

        base_7, partial_7 = _pick_base(snaps, base_7d_date)
        base_1, _ = _pick_base(snaps, base_1d_date)

        stars_7d = max(current.total_stars - base_7.total_stars, 0) if base_7 else 0
        stars_1d = max(current.total_stars - base_1.total_stars, 0) if base_1 else 0
        base_stars = base_7.total_stars if base_7 else max(current.total_stars - stars_7d, 1)

        repo.total_stars = current.total_stars
        repo.forks_count = current.forks_count
        repo.open_issues_count = current.open_issues_count
        repo.stars_7d = stars_7d
        repo.stars_1d = stars_1d
        repo.stars_7d_rate = safe_rate(stars_7d, max(base_stars, 1))
        repo.is_partial = partial_7
        repo.updated_at = now
        updated += 1

    await session.commit()
    logger.info("增量计算完成，共更新 %s 个仓库", updated)
    return updated


async def repo_trend(session: AsyncSession, repo_id: int, days: int = 8) -> list[dict]:
    """返回某个仓库最近 N 天的 Star 曲线（用于前端迷你趋势图）。"""
    snaps = await snapshot_repo.recent_snapshots(session, repo_id, days=days)
    trend: list[dict] = []
    previous: int | None = None
    for snap in snaps:
        delta = 0 if previous is None else max(snap.total_stars - previous, 0)
        trend.append(
            {
                "date": snap.snapshot_date,
                "total_stars": snap.total_stars,
                "delta": delta,
            }
        )
        previous = snap.total_stars
    return trend
