"""仓库相关的数据访问层。"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite import Favorite
from app.models.repo import Repo

# 允许在列表中直接返回/更新的字段白名单
_UPDATABLE_FIELDS = (
    "full_name",
    "owner",
    "name",
    "description",
    "language",
    "html_url",
    "homepage",
    "avatar_url",
    "topics",
    "license",
    "total_stars",
    "forks_count",
    "open_issues_count",
    "stars_1d",
    "stars_7d",
    "stars_7d_rate",
    "is_partial",
    "repo_created_at",
    "pushed_at",
)


def _chunk(items: Sequence[Any], size: int = 500):
    """按固定大小切分序列，避免 SQL 的 IN 列表过长。"""
    for i in range(0, len(items), size):
        yield items[i : i + size]


def normalize_repo_payload(data: dict[str, Any]) -> dict[str, Any]:
    """把 Github API 返回的仓库对象转换成 Repo 表字段字典。"""
    owner_info = data.get("owner") or {}
    topics = data.get("topics") or []
    license_info = data.get("license") or {}
    return {
        "repo_id": int(data["id"]),
        "full_name": data.get("full_name") or "",
        "owner": (data.get("owner") or {}).get("login") or owner_info.get("login") or "",
        "name": data.get("name") or "",
        "description": (data.get("description") or "").strip() or None,
        "language": data.get("language") or "Unknown",
        "html_url": data.get("html_url") or "",
        "homepage": data.get("homepage") or None,
        "avatar_url": owner_info.get("avatar_url") or None,
        "topics": json.dumps(topics, ensure_ascii=False) if topics else None,
        "license": (license_info.get("name") if isinstance(license_info, dict) else None) or None,
        "total_stars": int(data.get("stargazers_count") or 0),
        "forks_count": int(data.get("forks_count") or 0),
        "open_issues_count": int(data.get("open_issues_count") or 0),
        "repo_created_at": data.get("created_at"),
        "pushed_at": data.get("pushed_at"),
    }


async def upsert_repos(session: AsyncSession, payloads: Iterable[dict[str, Any]]) -> list[Repo]:
    """批量写入/更新仓库（幂等）。返回本次涉及到的 Repo 对象列表。"""
    payload_list = [normalize_repo_payload(p) for p in payloads if p.get("id")]
    if not payload_list:
        return []

    # 先按 repo_id 查出已存在的记录
    existing_map: dict[int, Repo] = {}
    ids = [p["repo_id"] for p in payload_list]
    for chunk in _chunk(ids, 400):
        rows = (await session.execute(select(Repo).where(Repo.repo_id.in_(chunk)))).scalars().all()
        for row in rows:
            existing_map[row.repo_id] = row

    result: list[Repo] = []
    for payload in payload_list:
        repo = existing_map.get(payload["repo_id"])
        if repo is None:
            repo = Repo(**payload)
            session.add(repo)
            existing_map[payload["repo_id"]] = repo
        else:
            for field in _UPDATABLE_FIELDS:
                if field in payload:
                    setattr(repo, field, payload[field])
        result.append(repo)

    await session.commit()
    return result


async def get_by_repo_id(session: AsyncSession, repo_id: int) -> Repo | None:
    """按 Github 仓库 ID 查询。"""
    return await session.scalar(select(Repo).where(Repo.repo_id == repo_id))


async def list_active_repos(session: AsyncSession, limit: int | None = None) -> list[Repo]:
    """查询所有仍在跟踪的仓库。"""
    stmt = select(Repo).where(Repo.is_active.is_(True))
    if limit:
        stmt = stmt.limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def count_repos(session: AsyncSession) -> int:
    """仓库总数。"""
    return int(await session.scalar(select(func.count(Repo.id))) or 0)


def build_query(
    *,
    languages: list[str] | None = None,
    keyword: str | None = None,
    sort_by: str = "stars_7d",
    order: str = "desc",
    only_favorites: bool = False,
    client_id: str | None = None,
    favorite_ids: set[int] | None = None,
) -> Select:
    """构造榜单查询（不执行），供 service 层复用。"""
    stmt = select(Repo).where(Repo.is_active.is_(True))

    if languages:
        stmt = stmt.where(Repo.language.in_(languages))

    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(or_(Repo.full_name.ilike(pattern), Repo.description.ilike(pattern)))

    if only_favorites:
        if favorite_ids:
            stmt = stmt.where(Repo.repo_id.in_(list(favorite_ids)))
        elif client_id:
            stmt = stmt.join(
                Favorite, Favorite.repo_id == Repo.repo_id
            ).where(Favorite.client_id == client_id)
        else:
            stmt = stmt.where(Repo.id == -1)  # 无 client_id 时返回空

    column = getattr(Repo, sort_by, Repo.stars_7d)
    # 追加唯一列作为次排序键：保证同分时分页结果稳定，避免翻页重复/漏项
    stmt = stmt.order_by(
        column.desc() if order == "desc" else column.asc(),
        Repo.repo_id.asc(),
    )
    return stmt


async def paging_query(
    session: AsyncSession, stmt: Select, page: int, page_size: int
) -> tuple[int, list[Repo]]:
    """执行分页查询，返回 (总数, 当前页数据)。"""
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(await session.scalar(count_stmt) or 0)

    offset = (page - 1) * page_size
    rows = (
        (await session.execute(stmt.offset(offset).limit(page_size))).scalars().all()
    )
    return total, list(rows)


async def distinct_languages(session: AsyncSession) -> list[tuple[str, int]]:
    """统计各语言的仓库数量（按数量降序）。"""
    rows = (
        await session.execute(
            select(Repo.language, func.count(Repo.id))
            .where(Repo.is_active.is_(True))
            .group_by(Repo.language)
            .order_by(func.count(Repo.id).desc())
        )
    ).all()
    return [(row[0] or "Unknown", int(row[1])) for row in rows]
