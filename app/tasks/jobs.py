"""定时任务实现：抓取快照、计算增量、清理历史数据。"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.repositories import meta_repo, snapshot_repo
from app.services.github.delta import compute_deltas
from app.services.github.sync import run_fetch_and_snapshot
from app.utils.time_util import days_ago_str, iso_or_empty, utc_now

logger = logging.getLogger(__name__)


async def _run_with_lock(task_name: str, coro_factory) -> None:
    """带数据库锁执行任务，避免同一任务并发/重复执行。"""
    async with AsyncSessionLocal() as lock_session:
        acquired = await meta_repo.try_acquire_lock(lock_session, task_name, ttl_seconds=3 * 3600)
    if not acquired:
        logger.info("任务 %s 正在执行中，本次跳过", task_name)
        return

    logger.info("任务 %s 开始执行", task_name)
    try:
        await coro_factory()
    except Exception as exc:  # noqa: BLE001 - 记录异常但不影响调度器
        logger.exception("任务 %s 执行失败: %s", task_name, exc)
    finally:
        async with AsyncSessionLocal() as lock_session:
            await meta_repo.release_lock(lock_session, task_name)
        logger.info("任务 %s 执行结束", task_name)


async def _do_fetch_snapshot() -> None:
    """抓取 Github 数据并写入今日快照（内部已包含增量计算）。"""
    result = await run_fetch_and_snapshot()
    logger.info("数据抓取结果: %s", result)


async def _do_compute_delta() -> None:
    """仅重算 7 日增量（不请求 Github）。"""
    async with AsyncSessionLocal() as session:
        count = await compute_deltas(session)
        await meta_repo.set_meta(session, "last_delta_at", iso_or_empty(utc_now()))
        logger.info("重算增量完成: %s 个仓库", count)


async def _do_cleanup() -> None:
    """清理过期快照与 API 缓存，控制数据库体积。"""
    settings = get_settings()
    cutoff = days_ago_str(settings.snapshot_retention_days)
    async with AsyncSessionLocal() as session:
        deleted = await snapshot_repo.delete_snapshots_before(session, cutoff)
        expired_cache = await meta_repo.cache_cleanup(session)
    logger.info(
        "清理完成：删除 %s 条过期快照（早于 %s），%s 条过期缓存", deleted, cutoff, expired_cache
    )


# ------------------------- 对外暴露的任务入口 -------------------------
async def job_fetch_snapshot() -> None:
    """定时任务：每日抓取 Github 数据。"""
    await _run_with_lock("fetch_snapshot", _do_fetch_snapshot)


async def job_compute_delta() -> None:
    """定时任务：每日计算 7 日新增 Star。"""
    await _run_with_lock("compute_delta", _do_compute_delta)


async def job_cleanup() -> None:
    """定时任务：每周清理历史数据。"""
    await _run_with_lock("cleanup", _do_cleanup)
