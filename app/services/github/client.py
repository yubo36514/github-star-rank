"""Github 官方 API 客户端。

职责：
1. 统一发起 HTTP 请求（带认证、超时、重试、退避）
2. 基于数据库的响应缓存，减少对 Github API 的重复请求
3. 读取 X-RateLimit-* 响应头进行配额管理，遇到限流主动停止任务
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.core.errors import GithubRateLimitError
from app.db.session import AsyncSessionLocal
from app.repositories import meta_repo

logger = logging.getLogger(__name__)

# Github 建议的请求头
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "github-star-ranking/0.1",
}


class GithubClient:
    """异步 Github API 客户端（进程内单例使用）。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        # 串行化所有请求，配合最小请求间隔规避 secondary rate limit
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0
        # 配额状态（内存缓存，避免每请求都查库）
        self._rate_remaining: int | None = None
        self._rate_reset_at: int | None = None
        self._rate_limit: int | None = None
        self._client: httpx.AsyncClient | None = None

    # ------------------------- 生命周期 -------------------------
    async def _http(self) -> httpx.AsyncClient:
        """懒加载 httpx 客户端（复用连接池）。"""
        if self._client is None or self._client.is_closed:
            headers = dict(DEFAULT_HEADERS)
            if self.settings.github_token:
                headers["Authorization"] = f"Bearer {self.settings.github_token}"
            self._client = httpx.AsyncClient(
                base_url=self.settings.github_api_base,
                headers=headers,
                timeout=httpx.Timeout(20.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """关闭 HTTP 客户端。"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    # ------------------------- 限流 -------------------------
    async def _throttle(self) -> None:
        """请求前检查配额并做最小间隔等待。"""
        # 内存中没有配额信息时，从数据库恢复上一次记录
        if self._rate_remaining is None:
            async with AsyncSessionLocal() as session:
                raw = await meta_repo.get_meta(session, "github_rate_remaining", "-1")
                reset_raw = await meta_repo.get_meta(session, "github_rate_reset_at", "")
            self._rate_remaining = int(raw) if raw.isdigit() else None
            self._rate_reset_at = int(reset_raw) if reset_raw.isdigit() else None

        if (
            self._rate_remaining is not None
            and self._rate_remaining <= self.settings.github_rate_limit_threshold
        ):
            reset_at = self._rate_reset_at or 0
            if reset_at and time.time() < reset_at:
                wait = int(reset_at - time.time())
                logger.warning(
                    "Github API 配额不足（remaining=%s，%ss 后重置），停止本轮请求",
                    self._rate_remaining,
                    wait,
                )
                raise GithubRateLimitError(
                    f"Github API 配额不足（剩余 {self._rate_remaining}，约 {wait}s 后重置）"
                )

        interval = max(self.settings.github_request_interval, 0.0)
        if interval > 0:
            delta = time.monotonic() - self._last_request_at
            if delta < interval:
                await asyncio.sleep(interval - delta)

    def _update_rate_state(self, headers: httpx.Headers) -> None:
        """从响应头更新配额状态，并异步持久化到数据库。"""
        remaining = headers.get("X-RateLimit-Remaining")
        limit = headers.get("X-RateLimit-Limit")
        reset = headers.get("X-RateLimit-Reset")
        if remaining is not None and remaining.isdigit():
            self._rate_remaining = int(remaining)
        if limit is not None and limit.isdigit():
            self._rate_limit = int(limit)
        if reset is not None and reset.isdigit():
            self._rate_reset_at = int(reset)

    async def _persist_rate_state(self) -> None:
        """把配额状态写入 meta_info，供前端 / 管理接口展示。"""
        if self._rate_remaining is None:
            return
        try:
            async with AsyncSessionLocal() as session:
                await meta_repo.set_meta_batch(
                    session,
                    {
                        "github_rate_remaining": str(self._rate_remaining),
                        "github_rate_limit": str(self._rate_limit or -1),
                        "github_rate_reset_at": str(self._rate_reset_at or ""),
                    },
                )
        except Exception as exc:  # 配额持久化失败不应影响主流程
            logger.debug("持久化 Github 配额失败: %s", exc)

    # ------------------------- 缓存 -------------------------
    @staticmethod
    def _cache_key(method: str, url: str, params: dict[str, Any] | None) -> str:
        """根据请求生成稳定的缓存 key。"""
        raw = f"{method}:{url}:{json.dumps(params or {}, sort_keys=True, ensure_ascii=False)}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    async def _cache_read(self, key: str) -> Any | None:
        """读取缓存（带默认 TTL 的响应缓存）。"""
        async with AsyncSessionLocal() as session:
            return await meta_repo.cache_get(session, key)

    async def _cache_write(self, key: str, payload: Any, ttl: int) -> None:
        """写入缓存。"""
        async with AsyncSessionLocal() as session:
            await meta_repo.cache_set(session, key, payload, ttl)

    # ------------------------- 核心请求 -------------------------
    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        ttl: int | None = None,
        use_cache: bool = True,
        max_retries: int = 3,
    ) -> Any:
        """发起请求，返回 JSON 数据；404 返回 None；限流抛出 GithubRateLimitError。

        :param ttl: 缓存秒数，None 表示使用全局默认 GITHUB_CACHE_TTL
        :param use_cache: 是否启用缓存（写操作请关闭）
        """
        cache_key = self._cache_key(method, url, params)
        cache_ttl = self.settings.github_cache_ttl if ttl is None else ttl

        if use_cache and cache_ttl > 0:
            cached = await self._cache_read(cache_key)
            if cached is not None:
                logger.debug("命中缓存: %s %s", method, url)
                return cached

        client = await self._http()
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            async with self._lock:
                await self._throttle()
                try:
                    response = await client.request(method, url, params=params)
                finally:
                    self._last_request_at = time.monotonic()

            self._update_rate_state(response.headers)
            status = response.status_code

            if status == 200:
                data = response.json()
                if use_cache and cache_ttl > 0:
                    await self._cache_write(cache_key, data, cache_ttl)
                await self._persist_rate_state()
                return data

            if status == 404:
                logger.info("Github 资源不存在: %s", url)
                return None

            if status in (403, 429):
                # 主配额耗尽或 secondary rate limit
                reset_at = self._rate_reset_at or int(time.time()) + 60
                wait = max(reset_at - int(time.time()), 5)
                logger.warning("Github API 限流 status=%s，%ss 后重置", status, wait)
                await self._persist_rate_state()
                if attempt >= max_retries:
                    raise GithubRateLimitError(f"Github API 限流（HTTP {status}），请稍后再试")
                await asyncio.sleep(min(wait, 30))
                last_error = GithubRateLimitError()
                continue

            if status >= 500:
                logger.warning("Github 服务端错误 %s，第 %s 次重试", status, attempt)
                last_error = RuntimeError(f"HTTP {status}")
                await asyncio.sleep(min(2**attempt, 10))
                continue

            # 其它 4xx：直接抛错，重试无意义
            logger.error("Github 请求失败 status=%s url=%s body=%s", status, url, response.text[:200])
            raise RuntimeError(f"Github 请求失败: HTTP {status}")

        raise last_error or RuntimeError("Github 请求失败")

    # ------------------------- 业务封装 -------------------------
    async def search_repositories(
        self,
        query: str,
        *,
        sort: str = "stars",
        order: str = "desc",
        page: int = 1,
        per_page: int = 100,
        ttl: int | None = None,
    ) -> dict[str, Any]:
        """调用 Search API 搜索仓库。

        官方文档: https://docs.github.com/rest/search/search#search-repositories
        """
        return (
            await self.request(
                "GET",
                "/search/repositories",
                params={
                    "q": query,
                    "sort": sort,
                    "order": order,
                    "page": page,
                    "per_page": per_page,
                },
                ttl=ttl,
            )
            or {"items": []}
        )

    async def get_repository(self, full_name: str, *, ttl: int | None = None) -> dict[str, Any] | None:
        """获取单个仓库详情。

        官方文档: https://docs.github.com/rest/repos/repos#get-a-repository
        """
        return await self.request("GET", f"/repos/{full_name}", ttl=ttl)

    async def get_stargazers(
        self, full_name: str, page: int = 1, per_page: int = 100
    ) -> list[dict[str, Any]] | None:
        """获取 Star 列表（带 starred_at 时间，用于新仓库估算 7 日增量）。

        需要 Accept: application/vnd.github.star+json；按时间倒序返回。
        """
        client = await self._http()
        async with self._lock:
            await self._throttle()
            try:
                response = await client.request(
                    "GET",
                    f"/repos/{full_name}/stargazers",
                    params={"page": page, "per_page": per_page},
                    headers={"Accept": "application/vnd.github.star+json"},
                )
            finally:
                self._last_request_at = time.monotonic()

        self._update_rate_state(response.headers)
        if response.status_code in (403, 429):
            raise GithubRateLimitError("Github API 限流，无法获取 stargazers")
        if response.status_code >= 400:
            return None
        return response.json()
