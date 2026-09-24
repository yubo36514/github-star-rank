"""Github 全网搜索接口（只读代理）。

设计要点：
1. 只调用 Github Search API 并把结果映射成输出模型，**不写数据库、不触发快照与增量计算**，
   因此不会影响定时任务与榜单数据。
2. 复用 GithubClient：自带响应缓存（api_cache 表，默认 TTL 6h）与限流退避，
   重复搜索同一关键词不会重复消耗 Github 配额。
3. 单次只取 1 页、默认 10 条（上限 20），把配额消耗压到最低。
4. GithubRateLimitError 直接冒泡，由全局异常处理器转成 42901 + 友好文案。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

from app.api.response import ok
from app.config import get_settings
from app.core.constants import language_color
from app.repositories.repo_repo import normalize_repo_payload
from app.schemas import RemoteRepoOut, RemoteSearchOut
from app.services.github.client import GithubClient
from app.utils.number_util import format_stars

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["搜索"])


def _to_remote_out(item: dict[str, Any]) -> RemoteRepoOut | None:
    """把 Github Search API 返回的仓库对象映射成输出模型（不做任何落库操作）。"""
    try:
        data = normalize_repo_payload(item)
    except (KeyError, TypeError, ValueError):  # 数据异常时跳过该条，不影响整体
        return None

    topics = item.get("topics") or []
    language = data.get("language") or "Unknown"
    return RemoteRepoOut(
        repo_id=data["repo_id"],
        full_name=data["full_name"],
        owner=data["owner"],
        name=data["name"],
        description=data["description"],
        language=language,
        language_color=language_color(language),
        html_url=data["html_url"],
        avatar_url=data["avatar_url"],
        homepage=data["homepage"],
        topics=[str(topic) for topic in topics][:8],
        license=data["license"],
        total_stars=data["total_stars"],
        total_stars_text=format_stars(data["total_stars"]),
        forks_count=data["forks_count"],
        open_issues_count=data["open_issues_count"],
    )


@router.get("/github", summary="Github 全网仓库搜索")
async def search_github(
    keyword: str = Query(..., min_length=2, max_length=100, description="搜索关键词，至少 2 个字符"),
    per_page: int = Query(10, ge=1, le=20, description="返回条数，上限 20（控制 Github 配额）"),
) -> dict:
    """检索 Github 全网仓库（只读，不入库）；与本地库检索互不干扰。"""
    settings = get_settings()

    # 功能开关：关闭时只返回标记，前端降级为「仅本地库检索」
    if not settings.github_remote_search_enabled:
        return ok(
            RemoteSearchOut(
                keyword=keyword,
                disabled=True,
                message="全网搜索已关闭（GITHUB_REMOTE_SEARCH_ENABLED=false），当前仅检索本地库",
            ).model_dump()
        )

    limit = min(per_page, settings.github_remote_search_per_page)
    client = GithubClient(settings)
    try:
        data = await client.search_repositories(
            keyword, sort="stars", order="desc", page=1, per_page=limit
        )
    except Exception as exc:
        # 限流 / 网络异常都只记日志，交由全局异常处理器统一返回
        logger.warning("Github 全网搜索失败: keyword=%s err=%s", keyword, exc)
        raise
    finally:
        await client.close()

    items = [
        out for out in (_to_remote_out(item) for item in (data.get("items") or [])) if out is not None
    ]
    return ok(RemoteSearchOut(keyword=keyword, total=len(items), items=items).model_dump())
