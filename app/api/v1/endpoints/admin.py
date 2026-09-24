"""管理接口：手动触发数据刷新、查看定时任务。

需要请求头：X-Admin-Token: <ADMIN_TOKEN>
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.api.deps import require_admin
from app.api.response import ok
from app.services.github.sync import run_fetch_and_snapshot
from app.tasks import scheduler as scheduler_module

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["管理"])


class RefreshRequest(BaseModel):
    """手动刷新请求体。"""

    force: bool = False  # True 表示忽略「今日已抓取」判断
    backfill: bool | None = None  # 是否估算新仓库的 7 日增量


async def _run_refresh(force: bool, backfill: bool | None) -> None:
    """后台执行数据刷新，避免接口长时间阻塞。"""
    result = await run_fetch_and_snapshot(force=force, backfill=backfill)
    logger.info("手动刷新完成: %s", result)


@router.post("/refresh", summary="手动触发数据抓取")
async def refresh(
    payload: RefreshRequest,
    background_tasks: BackgroundTasks,
    _token: str = Depends(require_admin),
) -> dict:
    """手动触发一轮 Github 数据抓取（异步执行，立即返回）。"""
    background_tasks.add_task(_run_refresh, payload.force, payload.backfill)
    return ok({"accepted": True, "force": payload.force}, message="刷新任务已在后台启动")


@router.get("/scheduler", summary="查看定时任务")
async def scheduler_status(_token: str = Depends(require_admin)) -> dict:
    """返回 APScheduler 中已注册的任务与下次执行时间。"""
    return ok(scheduler_module.scheduler_jobs())
