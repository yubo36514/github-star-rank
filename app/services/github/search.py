"""候选仓库发现：通过 Github Search API 构建「待跟踪仓库池」。

Github 没有官方 Trending API，因此采用多条搜索条件组合，尽量覆盖
「近期新建且爆火」「存量项目近期活跃」两类可能高速增长的仓库。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import Settings, get_settings
from app.services.github.client import GithubClient
from app.utils.time_util import days_ago_str

logger = logging.getLogger(__name__)


def build_queries(days_recent: int = 7, days_created: int = 60) -> list[str]:
    """构造搜索语句列表（Github 搜索语法）。"""
    pushed = days_ago_str(days_recent)
    created = days_ago_str(days_created)
    return [
        # 近期新建且已经积累一定 Star 的「新星项目」
        f"created:>{created} stars:>100",
        # 近期有提交的中大型活跃项目（最容易暴涨）
        f"pushed:>{pushed} stars:>1000",
        # 近期有提交的中腰部项目
        f"pushed:>{pushed} stars:200..1000",
        # 近一年新建的高星项目
        f"created:>{days_ago_str(365)} stars:>3000",
    ]


async def discover_candidates(
    client: GithubClient,
    *,
    settings: Settings | None = None,
    max_repos: int | None = None,
    pages: int | None = None,
    cache_ttl: int | None = None,
) -> list[dict[str, Any]]:
    """发现候选仓库（结果已按 repo id 去重）。

    :param max_repos: 候选池上限，默认取配置 GITHUB_MAX_REPOS
    :param pages: 每条搜索语句最多翻页数，默认取配置 GITHUB_SEARCH_PAGES
    """
    settings = settings or get_settings()
    max_repos = max_repos or settings.github_max_repos
    pages = pages or settings.github_search_pages
    # Search 结果缓存 6 小时，一天抓取两次也不会重复消耗配额
    ttl = settings.github_cache_ttl if cache_ttl is None else cache_ttl

    candidates: dict[int, dict[str, Any]] = {}
    for query in build_queries():
        for page in range(1, pages + 1):
            try:
                data = await client.search_repositories(
                    query, sort="stars", order="desc", page=page, per_page=100, ttl=ttl
                )
            except Exception as exc:  # 限流 / 网络错误时保留已获取结果
                logger.warning("搜索失败，跳过后续分页: q=%s page=%s err=%s", query, page, exc)
                break

            items = data.get("items") or []
            if not items:
                break

            for item in items:
                candidates.setdefault(int(item["id"]), item)

            logger.info("搜索命中: q=%s page=%s 累计候选=%s", query, page, len(candidates))
            if len(candidates) >= max_repos or len(items) < 100:
                break

            # Search API 限额更严格（30 次/分钟），主动拉大间隔
            await asyncio.sleep(max(settings.github_search_interval, 0))

        if len(candidates) >= max_repos:
            break

    logger.info("候选池构建完成，共 %s 个仓库", len(candidates))
    return list(candidates.values())[:max_repos]
