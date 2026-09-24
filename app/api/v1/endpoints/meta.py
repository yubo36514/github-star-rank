"""元数据接口：全局统计、健康检查。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.response import ok
from app.services import stats_service

router = APIRouter(prefix="/meta", tags=["元数据"])


@router.get("/stats", summary="全局统计")
async def stats(session: AsyncSession = Depends(get_session)) -> dict:
    """返回收录数量、最近抓取时间、Github 配额等信息。"""
    data = await stats_service.get_stats(session)
    return ok(data.model_dump())


@router.get("/health", summary="健康检查")
async def health(session: AsyncSession = Depends(get_session)) -> dict:
    """健康检查（同时验证数据库可用）。"""
    data = await stats_service.get_stats(session)
    return ok({"status": "ok", "repo_count": data.repo_count})
