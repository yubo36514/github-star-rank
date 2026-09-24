"""演示数据种子。

用途：首次启动（或数据库为空）时写入一批模拟仓库与近 8 天快照，
确保「一键启动即可看到完整榜单效果」，无需等待 Github 数据累积 7 天。
生产环境可通过 DEMO_SEED_ON_EMPTY=false 关闭。
"""

from __future__ import annotations

import logging
import random
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repo import Repo
from app.models.snapshot import RepoSnapshot
from app.repositories import repo_repo
from app.services.github.delta import compute_deltas
from app.utils.time_util import days_ago_str, utc_now

logger = logging.getLogger(__name__)

# (owner, repo, 语言, 简介关键词)
_DEMO_TEMPLATES: list[tuple[str, str, str, str]] = [
    ("vercel", "next.js", "TypeScript", "The React Framework for the Web"),
    ("facebook", "react", "JavaScript", "The library for web and native user interfaces"),
    ("vuejs", "core", "Vue", "Progressive JavaScript framework"),
    ("sveltejs", "svelte", "JavaScript", "Cybernetically enhanced web apps"),
    ("rust-lang", "rust", "Rust", "Empowering everyone to build reliable software"),
    ("golang", "go", "Go", "The Go programming language"),
    ("python", "cpython", "Python", "The Python programming language"),
    ("denoland", "deno", "Rust", "A modern runtime for JavaScript and TypeScript"),
    ("bun", "bun", "Zig", "Incredibly fast JavaScript runtime, bundler and package manager"),
    ("oven-sh", "bun", "Zig", "Incredibly fast JavaScript all-in-one toolkit"),
    ("langchain-ai", "langchain", "Python", "Build context-aware reasoning applications"),
    ("openai", "whisper", "Python", "Robust Speech Recognition via Large-Scale Weak Supervision"),
    ("ggml-org", "llama.cpp", "C++", "LLM inference in C/C++"),
    ("vllm-project", "vllm", "Python", "A high-throughput LLM serving engine"),
    ("ollama", "ollama", "Go", "Run large language models locally"),
    ("huggingface", "transformers", "Python", "State-of-the-art Machine Learning for PyTorch"),
    ("pytorch", "pytorch", "Python", "Tensors and Dynamic neural networks"),
    ("tensorflow", "tensorflow", "C++", "An Open Source Machine Learning Framework"),
    ("scikit-learn", "scikit-learn", "Python", "Machine learning in Python"),
    ("fastapi", "fastapi", "Python", "FastAPI framework, high performance, easy to learn"),
    ("tiangolo", "fastapi", "Python", "Modern, fast web framework for building APIs"),
    ("django", "django", "Python", "The Web framework for perfectionists with deadlines"),
    ("pallets", "flask", "Python", "The Python micro framework for building web applications"),
    ("sqlalchemy", "sqlalchemy", "Python", "The Database Toolkit for Python"),
    ("astral-sh", "ruff", "Rust", "An extremely fast Python linter and formatter"),
    ("astral-sh", "uv", "Rust", "An extremely fast Python package manager"),
    ("psf", "requests", "Python", "A simple, yet elegant HTTP library"),
    ("encode", "httpx", "Python", "A next generation HTTP client for Python"),
    ("home-assistant", "core", "Python", "Open source home automation"),
    ("apache", "airflow", "Python", "Platform to programmatically author workflows"),
    ("ray-project", "ray", "Python", "A unified framework for scaling AI workloads"),
    ("ansible", "ansible", "Python", "Radically simple IT automation"),
    ("kubernetes", "kubernetes", "Go", "Production-Grade Container Orchestration"),
    ("docker", "compose", "Go", "Define and run multi-container applications"),
    ("grafana", "grafana", "TypeScript", "The open observability platform"),
    ("prometheus", "prometheus", "Go", "Systems monitoring and alerting toolkit"),
    ("hashicorp", "terraform", "Go", "Infrastructure as Code for everyone"),
    ("etcd-io", "etcd", "Go", "Distributed reliable key-value store"),
    ("redis", "redis", "C", "In-memory data structure store"),
    ("ClickHouse", "ClickHouse", "C++", "ClickHouse — open source column-oriented DBMS"),
    ("duckdb", "duckdb", "C++", "An in-process SQL OLAP database management system"),
    ("sqlite", "sqlite", "C", "Official Git mirror of the SQLite source tree"),
    ("postgres", "postgres", "C", "Mirror of the official PostgreSQL GIT repository"),
    ("supabase", "supabase", "TypeScript", "The open source Firebase alternative"),
    ("appwrite", "appwrite", "TypeScript", "Backend server for Web, Mobile & Flutter apps"),
    ("n8n-io", "n8n", "TypeScript", "Fair-code workflow automation platform"),
    ("zed-industries", "zed", "Rust", "Code at the speed of thought"),
    ("neovim", "neovim", "C", "Vim-fork focused on extensibility and usability"),
    ("microsoft", "vscode", "TypeScript", "Visual Studio Code"),
    ("jetbrains", "kotlin", "Kotlin", "The Kotlin Programming Language"),
    ("apple", "swift", "C++", "The Swift Programming Language"),
    ("flutter", "flutter", "Dart", "Flutter makes it easy to build beautiful apps"),
    ("tailwindlabs", "tailwindcss", "TypeScript", "A utility-first CSS framework"),
    ("unocss", "unocss", "TypeScript", "The instant on-demand atomic CSS engine"),
    ("vitejs", "vite", "TypeScript", "Next generation frontend tooling"),
    ("web-infra-dev", "rspack", "Rust", "A fast Rust-based web bundler"),
    ("rollup", "rollup", "JavaScript", "Next-generation ES module bundler"),
    ("esbuild", "esbuild", "Go", "An extremely fast JavaScript bundler"),
    ("swc-project", "swc", "Rust", "Rust-based platform for the Web"),
    ("biomejs", "biome", "Rust", "Toolchain of the web: formatter, linter and more"),
    ("storybookjs", "storybook", "TypeScript", "Workshop for building UI components"),
    ("testing-library", "react-testing-library", "JavaScript", "Simple and complete testing utilities"),
    ("playwright", "playwright", "TypeScript", "Framework for Web Testing and Automation"),
    ("cypress-io", "cypress", "TypeScript", "Fast, easy and reliable testing for anything in browser"),
    ("nocodb", "nocodb", "TypeScript", "The Open Source Airtable alternative"),
    ("appsmithorg", "appsmith", "TypeScript", "Build internal tools and admin panels"),
    ("directus", "directus", "TypeScript", "Open Data Platform for headless content"),
    ("strapi", "strapi", "JavaScript", "The leading open-source headless CMS"),
    ("ghost", "Ghost", "JavaScript", "Independent technology for modern publishing"),
    ("openssl", "openssl", "C", "TLS/SSL and crypto library"),
    ("curl", "curl", "C", "Command line tool and library for transferring data"),
]

_TOPIC_POOL = [
    "ai", "llm", "machine-learning", "web", "framework", "cli", "database",
    "devops", "tooling", "rust", "python", "typescript", "self-hosted",
    "productivity", "api", "frontend", "backend", "observability",
]


def _build_demo_records(count: int = 120) -> list[dict]:
    """构造演示仓库数据（确定性随机，保证每次结果一致）。"""
    rng = random.Random(20240923)
    records: list[dict] = []
    for index in range(count):
        owner, name, language, base_desc = _DEMO_TEMPLATES[index % len(_DEMO_TEMPLATES)]
        suffix = "" if index < len(_DEMO_TEMPLATES) else f"-{index // len(_DEMO_TEMPLATES)}"
        full_name = f"{owner}/{name}{suffix}"
        total_stars = rng.randint(800, 90_000)
        growth_7d = int(total_stars * rng.uniform(0.005, 0.09))
        records.append(
            {
                "repo_id": 1_000_000 + index,
                "full_name": full_name,
                "owner": owner,
                "name": f"{name}{suffix}",
                "description": f"{base_desc}（演示数据 #{index + 1}）",
                "language": language,
                "html_url": f"https://github.com/{full_name}",
                "homepage": None,
                "avatar_url": f"https://avatars.githubusercontent.com/u/{1000 + index}?v=4",
                "topics": '["' + '", "'.join(rng.sample(_TOPIC_POOL, 3)) + '"]',
                "license": rng.choice(["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0"]),
                "total_stars": total_stars,
                "forks_count": int(total_stars * rng.uniform(0.05, 0.25)),
                "open_issues_count": rng.randint(10, 1500),
                "repo_created_at": (utc_now() - timedelta(days=rng.randint(200, 3000))).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "pushed_at": (utc_now() - timedelta(days=rng.randint(0, 20))).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "growth_7d": growth_7d,
            }
        )
    return records


async def seed_demo_data(session: AsyncSession, count: int = 120, history_days: int = 8) -> int:
    """写入演示仓库与近 N 天快照，返回仓库数量。"""
    records = _build_demo_records(count)
    now = utc_now()
    # repo_id -> 7 日目标增量（写快照时按天分摊）
    growth_map: dict[int, int] = {}

    for record in records:
        growth_map[record["repo_id"]] = record.pop("growth_7d")
        session.add(
            Repo(**record, first_seen_at=now - timedelta(days=history_days), updated_at=now)
        )
    await session.commit()

    # 写入历史快照：越靠近今天 Star 越多，7 日前的快照 = 今日 Star - growth
    for record in records:
        total = record["total_stars"]
        growth = growth_map[record["repo_id"]]
        for day_offset in range(history_days - 1, -1, -1):
            date_str = days_ago_str(day_offset)
            stars = total - int(growth * day_offset / max(history_days - 1, 1))
            session.add(
                RepoSnapshot(
                    repo_id=record["repo_id"],
                    snapshot_date=date_str,
                    total_stars=max(stars, 0),
                    forks_count=record["forks_count"],
                    open_issues_count=record["open_issues_count"],
                    fetched_at=now,
                )
            )
    await session.commit()

    await compute_deltas(session)
    logger.info("已写入演示数据：%s 个仓库，每个 %s 天快照", len(records), history_days)
    return len(records)


async def seed_demo_data_if_empty(session: AsyncSession) -> bool:
    """仅在数据库为空时写入演示数据，返回是否执行了写入。"""
    total = await repo_repo.count_repos(session)
    if total > 0:
        return False
    await seed_demo_data(session)
    return True
