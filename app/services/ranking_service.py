"""榜单业务层：列表查询、详情、语言筛选。"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, DEFAULT_SORT_BY, SORTABLE_FIELDS, language_color
from app.repositories import favorite_repo, meta_repo, repo_repo
from app.schemas import LanguageOut, RepoDetailOut, RepoListOut, to_repo_out
from app.services.github.delta import repo_trend
from app.utils.time_util import iso_or_empty, utc_now

logger = logging.getLogger(__name__)


def normalize_sort(sort_by: str | None) -> str:
    """校验并归一化排序字段，非法值回退到默认排序。"""
    if sort_by and sort_by in SORTABLE_FIELDS:
        return SORTABLE_FIELDS[sort_by]  # type: ignore[index]
    return SORTABLE_FIELDS[DEFAULT_SORT_BY]


def normalize_page_size(page_size: int | None) -> int:
    """限制每页条数在合法范围内。"""
    if not page_size or page_size <= 0:
        return DEFAULT_PAGE_SIZE
    return min(page_size, 100)


async def list_repos(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    languages: list[str] | None = None,
    keyword: str | None = None,
    sort_by: str = DEFAULT_SORT_BY,
    order: str = "desc",
    only_favorites: bool = False,
    client_id: str | None = None,
) -> RepoListOut:
    """分页查询榜单，返回前端渲染所需的完整结构。"""
    page = max(page, 1)
    page_size = normalize_page_size(page_size)
    column = normalize_sort(sort_by)
    order = "asc" if order == "asc" else "desc"

    # 先取当前客户端的收藏集合，用于给卡片打标（避免 N+1 查询）
    favorite_ids: set[int] = set()
    if client_id:
        favorite_ids = set(await favorite_repo.list_repo_ids(session, client_id))

    stmt = repo_repo.build_query(
        languages=languages,
        keyword=keyword,
        sort_by=column,
        order=order,
        only_favorites=only_favorites,
        client_id=client_id,
        favorite_ids=favorite_ids,
    )
    total, repos = await repo_repo.paging_query(session, stmt, page, page_size)
    total_pages = (total + page_size - 1) // page_size if page_size else 1

    start_rank = (page - 1) * page_size + 1
    items = [
        to_repo_out(repo, is_favorite=repo.repo_id in favorite_ids, rank=start_rank + index)
        for index, repo in enumerate(repos)
    ]

    last_fetch_at = await meta_repo.get_meta(session, "last_fetch_at", "")
    return RepoListOut(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        updated_at=last_fetch_at,
        items=items,
    )


async def get_repo_detail(
    session: AsyncSession, repo_id: int, client_id: str | None = None
) -> RepoDetailOut | None:
    """查询单个项目详情（含近 8 天 Star 趋势）。"""
    repo = await repo_repo.get_by_repo_id(session, repo_id)
    if repo is None:
        return None

    is_favorite = False
    if client_id:
        is_favorite = repo_id in set(await favorite_repo.list_repo_ids(session, client_id))

    trend = await repo_trend(session, repo_id, days=8)
    return RepoDetailOut(repo=to_repo_out(repo, is_favorite=is_favorite), trend=trend)


async def list_languages(session: AsyncSession) -> list[LanguageOut]:
    """返回可用于筛选的语言列表（带项目数量与展示色）。"""
    rows = await repo_repo.distinct_languages(session)
    return [
        LanguageOut(name=name, count=count, color=language_color(name))
        for name, count in rows
        if name
    ]


async def current_updated_at(session: AsyncSession) -> str:
    """返回数据更新时间字符串（供接口复用）。"""
    return await meta_repo.get_meta(session, "last_fetch_at", "") or iso_or_empty(utc_now())
