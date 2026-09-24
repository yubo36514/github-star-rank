"""APScheduler 调度器：随 FastAPI 应用生命周期启动/关闭。

所有时间使用 UTC（Asia/Shanghai = UTC+8），
因此配置里的 FETCH_CRON_HOUR=0 对应北京时间 08:00。
"""

from __future__ import annotations

import logging
from datetime import UTC

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.tasks.jobs import job_cleanup, job_compute_delta, job_fetch_snapshot

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def build_scheduler() -> AsyncIOScheduler:
    """创建调度器并注册全部定时任务。"""
    settings = get_settings()
    scheduler = AsyncIOScheduler(
        timezone=UTC, job_defaults={"coalesce": True, "max_instances": 1}
    )

    # 1) 每日抓取 Github 数据并写入快照
    scheduler.add_job(
        job_fetch_snapshot,
        CronTrigger(hour=settings.fetch_cron_hour, minute=10, timezone=UTC),
        id="fetch_snapshot",
        name="抓取 Github 每日快照",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # 2) 抓取完成后重算 7 日增量（兜底：即使抓取任务失败也能刷新指标）
    scheduler.add_job(
        job_compute_delta,
        CronTrigger(hour=settings.delta_cron_hour, minute=0, timezone=UTC),
        id="compute_delta",
        name="计算 7 日 Star 增量",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # 3) 每周清理过期快照与缓存（周一）
    scheduler.add_job(
        job_cleanup,
        CronTrigger(
            day_of_week="mon", hour=settings.cleanup_cron_hour, minute=0, timezone=UTC
        ),
        id="cleanup",
        name="清理过期数据",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info(
        "定时任务已注册：抓取(UTC %s:10) / 增量(UTC %s:00) / 清理(周一 UTC %s:00)",
        settings.fetch_cron_hour,
        settings.delta_cron_hour,
        settings.cleanup_cron_hour,
    )
    return scheduler


def start_scheduler() -> None:
    """启动调度器（重复调用安全）。"""
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = build_scheduler()
    _scheduler.start()
    logger.info("APScheduler 已启动")


def shutdown_scheduler() -> None:
    """关闭调度器。"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler 已关闭")
    _scheduler = None


def scheduler_jobs() -> list[dict]:
    """返回当前调度任务列表（便于管理接口查看）。"""
    if not _scheduler:
        return []
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time),
            "trigger": str(job.trigger),
        }
        for job in _scheduler.get_jobs()
    ]
