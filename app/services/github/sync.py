"""数据同步主流程：发现候选 -> 写入仓库 -> 写入每日快照 -> 计算 7 日增量。

设计要点：
1. 优先使用 Search API 返回的仓库对象（已包含 stargazers_count），
   避免对每个仓库再发一次详情请求 —— 这是减少 API 请求量的关键。
2. 只有当「已在库中跟踪、但今天没出现在搜索结果里」的仓库才走详情接口，且结果进缓存。
3. 新收录的仓库可用 stargazers 时间线接口估算近 7 日增量（可配置关闭）。
4. 全程捕获 GithubRateLimitError，配额耗尽时保留已抓到的数据并结束本轮。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import GithubRateLimitError
from app.db.session import AsyncSessionLocal
from app.models.repo import Repo
from app.repositories import meta_repo, repo_repo, snapshot_repo
from app.services.github.client import GithubClient
from app.services.github.delta import compute_deltas
from app.services.github.search import discover_candidates
from app.utils.time_util import iso_or_empty, today_str, utc_now

logger = logging.getLogger(__name__)


async def _write_snapshots_from_payload(
    session: AsyncSession, repos: list[Repo], payload_by_id: dict[int, dict[str, Any]], date_str: str
) -> int:
    """根据 Github 返回的原始数据批量写入今日快照。"""
    rows = []
    for repo in repos:
        payload = payload_by_id.get(repo.repo_id)
        if not payload:
            continue
        rows.append(
            {
                "repo_id": repo.repo_id,
                "snapshot_date": date_str,
                "total_stars": int(payload.get("stargazers_count") or 0),
                "forks_count": int(payload.get("forks_count") or 0),
                "open_issues_count": int(payload.get("open_issues_count") or 0),
            }
        )
    if not rows:
        return 0
    return await snapshot_repo.bulk_upsert(session, rows)


async def _sync_missing_repos(
    session: AsyncSession,
    client: GithubClient,
    date_str: str,
    already_synced: set[int],
    limit: int = 300,
    ttl: int | None = None,
) -> int:
    """为「已跟踪但今天未出现在搜索结果中」的仓库补一次快照（走缓存的详情接口）。"""
    repos = await repo_repo.list_active_repos(session)
    pending = [r for r in repos if r.repo_id not in already_synced][:limit]
    if not pending:
        return 0

    written = 0
    for index, repo in enumerate(pending, start=1):
        try:
            data = await client.get_repository(repo.full_name, ttl=ttl)
        except GithubRateLimitError as exc:
            logger.warning("配额不足，提前结束补全: %s", exc)
            break
        except Exception as exc:  # 单仓库失败不影响整体
            logger.warning("获取仓库详情失败 %s: %s", repo.full_name, exc)
            continue

        if not data:
            continue

        await snapshot_repo.upsert_snapshot(
            session,
            repo_id=repo.repo_id,
            snapshot_date=date_str,
            total_stars=int(data.get("stargazers_count") or 0),
            forks_count=int(data.get("forks_count") or 0),
            open_issues_count=int(data.get("open_issues_count") or 0),
        )
        # 顺带刷新仓库基础信息
        for key, value in repo_repo.normalize_repo_payload(data).items():
            setattr(repo, key, value)
        written += 1

        if index % 50 == 0:
            await session.commit()
            logger.info("补全进度 %s/%s", index, len(pending))

    await session.commit()
    return written


async def _estimate_stars_7d_by_stargazers(
    client: GithubClient, full_name: str, days: int = 7, max_pages: int = 10
) -> int | None:
    """用 stargazers 时间线接口估算近 N 日新增 Star 数。

    Github 按「最近的 Star 在前」返回，因此从第一页开始计数直到遇到早于 cutoff 的记录。
    最多翻 max_pages 页（100 条/页），即估算上限为 max_pages * 100。
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    total = 0
    for page in range(1, max_pages + 1):
        try:
            items = await client.get_stargazers(full_name, page=page, per_page=100)
        except GithubRateLimitError:
            return None
        except Exception as exc:
            logger.debug("获取 stargazers 失败 %s: %s", full_name, exc)
            return None

        if not items:
            break

        stop = False
        for item in items:
            starred_at = item.get("starred_at")
            if not starred_at:
                stop = True
                break
            try:
                starred_dt = datetime.fromisoformat(starred_at.replace("Z", "+00:00"))
            except ValueError:
                stop = True
                break
            if starred_dt >= cutoff:
                total += 1
            else:
                stop = True
                break
        if stop or len(items) < 100:
            break

        # stargazers 属于 core API，间隔可比 search 小
        await asyncio.sleep(0.5)

    return total


async def _backfill_new_repos(session: AsyncSession, client: GithubClient, limit: int) -> int:
    """为「今天首次收录」的仓库估算 7 日增量，避免新部署时榜单全为 0。"""
    if limit <= 0:
        return 0
    repos = await repo_repo.list_active_repos(session)
    fresh = [r for r in repos if r.stars_7d == 0 and r.is_partial][:limit]
    if not fresh:
        return 0

    updated = 0
    for repo in fresh:
        estimate = await _estimate_stars_7d_by_stargazers(client, repo.full_name)
        if not estimate:
            continue
        repo.stars_7d = estimate
        repo.stars_1d = max(estimate // 7, 0)
        repo.stars_7d_rate = round(estimate / max(repo.total_stars - estimate, 1), 6)
        updated += 1
    await session.commit()
    logger.info("新仓库 7 日增量估算完成，更新 %s 个", updated)
    return updated


async def run_fetch_and_snapshot(
    *, force: bool = False, backfill: bool | None = None, max_repos: int | None = None
) -> dict[str, Any]:
    """执行一次完整的数据同步。

    :param force: True 时忽略「今天已抓取过」的判断
    :param backfill: 是否对新仓库做 7 日增量估算；None 表示跟随配置
    :return: 同步结果统计
    """
    from app.config import get_settings

    settings = get_settings()
    today = today_str()
    started = utc_now()
    client = GithubClient(settings)
    summary: dict[str, Any] = {
        "date": today,
        "candidates": 0,
        "snapshots": 0,
        "backfilled": 0,
        "status": "success",
        "message": "",
        "duration_ms": 0,
    }

    try:
        async with AsyncSessionLocal() as session:
            # 1) 幂等保护：同一天重复触发时直接跳过（force 除外）
            if not force:
                last = await meta_repo.get_meta(session, "last_fetch_at", "")
                if last.startswith(today):
                    logger.info("今日(%s)已完成抓取，跳过", today)
                    summary["status"] = "skipped"
                    summary["message"] = "今日已抓取，使用 force=true 强制刷新"
                    return summary

            # 2) 发现候选仓库（force 时绕过 API 缓存，确保拿到最新数据）
            candidates = await discover_candidates(client, cache_ttl=0 if force else None)
            summary["candidates"] = len(candidates)
            if not candidates:
                summary["status"] = "partial"
                summary["message"] = "未获取到候选仓库（可能受 Github 配额限制）"
                return summary

            # 3) 写入/更新仓库主表
            repos = await repo_repo.upsert_repos(session, candidates)
            payload_by_id = {int(c["id"]): c for c in candidates}

            # 4) 写入今日快照（直接用搜索结果，不额外请求详情接口）
            written = await _write_snapshots_from_payload(session, repos, payload_by_id, today)
            summary["snapshots"] = written
            logger.info("已写入今日快照 %s 条", written)

            # 5) 为未出现在搜索结果中的已跟踪仓库补全快照
            summary["snapshots"] += await _sync_missing_repos(
                session,
                client,
                today,
                already_synced=set(payload_by_id.keys()),
                ttl=0 if force else None,
            )

            # 6) 计算 1 日 / 7 日增量
            updated = await compute_deltas(session)
            summary["delta_updated"] = updated

            # 7) 新仓库增量估算（可选）
            do_backfill = settings.github_backfill_stargazers if backfill is None else backfill
            if do_backfill:
                summary["backfilled"] = await _backfill_new_repos(
                    session, client, settings.github_backfill_limit
                )

            # 8) 更新元数据
            await meta_repo.set_meta_batch(
                session,
                {
                    "last_fetch_at": iso_or_empty(utc_now()),
                    "last_fetch_status": "success",
                    "last_fetch_count": str(written),
                },
            )
    except GithubRateLimitError as exc:
        logger.warning("Github 配额不足，本轮数据同步提前结束: %s", exc)
        summary["status"] = "partial"
        summary["message"] = str(exc)
        async with AsyncSessionLocal() as session:
            await meta_repo.set_meta_batch(
                session,
                {
                    "last_fetch_status": "partial",
                    "last_fetch_message": str(exc),
                },
            )
            # 即便未抓完，也用已有快照重算一次增量
            await compute_deltas(session)
    except Exception as exc:  # noqa: BLE001 - 兜底保证定时任务不中断
        logger.exception("数据同步失败: %s", exc)
        summary["status"] = "failed"
        summary["message"] = str(exc)
        async with AsyncSessionLocal() as session:
            await meta_repo.set_meta_batch(
                session,
                {
                    "last_fetch_status": "failed",
                    "last_fetch_message": str(exc),
                },
            )
    finally:
        await client.close()
        summary["duration_ms"] = int((utc_now() - started).total_seconds() * 1000)

    logger.info("数据同步完成: %s", summary)
    return summary
