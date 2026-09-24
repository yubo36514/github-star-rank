"""语言筛选接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.response import ok
from app.services import ranking_service

router = APIRouter(prefix="/languages", tags=["筛选"])


@router.get("", summary="可选编程语言列表")
async def list_languages(session: AsyncSession = Depends(get_session)) -> dict:
    """返回所有出现过的编程语言及其项目数量（按数量降序）。"""
    languages = await ranking_service.list_languages(session)
    return ok([item.model_dump() for item in languages])
