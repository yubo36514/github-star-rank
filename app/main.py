"""FastAPI 应用入口。

启动流程（lifespan）：
1. 初始化日志
2. 建表 & 写入默认元数据
3. 数据库为空时写入演示数据（可通过 DEMO_SEED_ON_EMPTY=false 关闭）
4. 启动 APScheduler 定时任务
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router, register_exception_handlers
from app.config import get_settings
from app.db.init_db import init_database
from app.db.session import AsyncSessionLocal, engine
from app.logging_config import setup_logging
from app.tasks.scheduler import shutdown_scheduler, start_scheduler

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201 - FastAPI 要求的生命周期签名
    """应用启动 / 关闭时的初始化与清理。"""
    setup_logging()
    logger.info("服务启动中，环境=%s", settings.app_env)

    # 1) 建表
    await init_database()

    # 2) 空库时写入演示数据，保证一键启动即可看到效果
    if settings.demo_seed_on_empty:
        from app.services.demo_seed import seed_demo_data_if_empty

        async with AsyncSessionLocal() as session:
            seeded = await seed_demo_data_if_empty(session)
        if seeded:
            logger.info("已写入演示数据（真实数据将在定时任务执行或手动刷新后生成）")

    # 3) 启动定时任务
    start_scheduler()

    yield

    shutdown_scheduler()
    await engine.dispose()
    logger.info("服务已停止")


app = FastAPI(
    title="Github 7 日新增 Star 项目榜单",
    description="定时抓取 Github 官方 API，统计近 7 日 Star 增量并生成榜单",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# 统一异常 -> {code, message, data}
register_exception_handlers(app)

# 前后端分离：允许浏览器直接访问接口（生产环境建议改成具体域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RESTful 接口
app.include_router(api_router, prefix="/api/v1")

# 前端静态页面（web/index.html）。放在最后挂载，避免覆盖 /api 路由
if settings.web_dir.exists():
    app.mount("/", StaticFiles(directory=str(settings.web_dir), html=True), name="web")
    logger.info("已挂载前端静态目录: %s", settings.web_dir)
else:  # pragma: no cover - 目录缺失时给出提示
    logger.warning("未找到前端目录: %s，仅提供 API 服务", settings.web_dir)


if __name__ == "__main__":  # 便于 `python -m app.main` 直接启动
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
