"""日志配置：统一的控制台日志格式，同时把日志写入 logs/app.log。"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.config import BASE_DIR, get_settings


def setup_logging() -> None:
    """初始化日志（可重复调用，内部做了幂等处理）。"""
    settings = get_settings()
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    if getattr(root, "_gh_rank_configured", False):  # 已经初始化过则直接返回
        return
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # 降低第三方库日志噪音
    for name in ("httpx", "apscheduler", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(logging.WARNING)

    root._gh_rank_configured = True  # type: ignore[attr-defined]
