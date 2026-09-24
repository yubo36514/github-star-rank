"""Pydantic 输出/输入模型。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import language_color


class RepoOut(BaseModel):
    """榜单卡片使用的仓库输出模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_id: int
    full_name: str
    owner: str
    name: str
    description: str | None = None
    language: str | None = None
    language_color: str = ""
    html_url: str
    homepage: str | None = None
    avatar_url: str | None = None
    topics: list[str] = Field(default_factory=list)
    license: str | None = None
    total_stars: int = 0
    total_stars_text: str = ""
    forks_count: int = 0
    open_issues_count: int = 0
    stars_1d: int = 0
    stars_7d: int = 0
    stars_7d_rate: float = 0.0
    is_partial: bool = False
    repo_created_at: str | None = None
    pushed_at: str | None = None
    first_seen_at: str | None = None
    updated_at: str | None = None
    is_favorite: bool = False
    rank: int = 0

    @field_validator("topics", mode="before")
    @classmethod
    def _parse_topics(cls, value: Any) -> list[str]:
        """数据库里 topics 是 JSON 字符串，这里转成列表。"""
        if not value:
            return []
        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @field_validator("first_seen_at", "updated_at", mode="before")
    @classmethod
    def _format_datetime(cls, value: Any) -> str | None:
        """datetime 转成接口友好的字符串。"""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value


def to_repo_out(repo: Any, *, is_favorite: bool = False, rank: int = 0) -> RepoOut:
    """把 ORM 对象转换成输出模型（补齐前端需要的派生字段）。"""
    from app.utils.number_util import format_stars

    data = {
        "id": repo.id,
        "repo_id": repo.repo_id,
        "full_name": repo.full_name,
        "owner": repo.owner,
        "name": repo.name,
        "description": repo.description,
        "language": repo.language or "Unknown",
        "language_color": language_color(repo.language),
        "html_url": repo.html_url,
        "homepage": repo.homepage,
        "avatar_url": repo.avatar_url,
        "topics": repo.topics,
        "license": repo.license,
        "total_stars": repo.total_stars,
        "total_stars_text": format_stars(repo.total_stars),
        "forks_count": repo.forks_count,
        "open_issues_count": repo.open_issues_count,
        "stars_1d": repo.stars_1d,
        "stars_7d": repo.stars_7d,
        "stars_7d_rate": repo.stars_7d_rate,
        "is_partial": repo.is_partial,
        "repo_created_at": repo.repo_created_at,
        "pushed_at": repo.pushed_at,
        "first_seen_at": repo.first_seen_at,
        "updated_at": repo.updated_at,
        "is_favorite": is_favorite,
        "rank": rank,
    }
    return RepoOut(**data)


class TrendPoint(BaseModel):
    """趋势图上的一个点。"""

    date: str
    total_stars: int
    delta: int


class RepoDetailOut(BaseModel):
    """项目详情（仓库信息 + 趋势数据）。"""

    repo: RepoOut
    trend: list[TrendPoint] = Field(default_factory=list)


class RepoListOut(BaseModel):
    """榜单列表响应体。"""

    total: int
    page: int
    page_size: int
    total_pages: int
    updated_at: str = ""
    items: list[RepoOut] = Field(default_factory=list)


class LanguageOut(BaseModel):
    """语言筛选项。"""

    name: str
    count: int
    color: str = ""


class StatsOut(BaseModel):
    """全局统计信息。"""

    repo_count: int = 0
    snapshot_count: int = 0
    favorite_count: int = 0
    last_fetch_at: str = ""
    last_fetch_status: str = ""
    github_rate_remaining: int = -1
    github_rate_limit: int = -1
    github_rate_reset_at: str = ""
    has_token: bool = False
