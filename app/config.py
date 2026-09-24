"""应用配置：全部从环境变量 / .env 文件读取（pydantic-settings，大小写不敏感）。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（app/ 的上一级）
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """全局配置对象，字段与环境变量同名（大写形式，如 APP_PORT）。"""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- 应用 ----------
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_workers: int = 1
    log_level: str = "INFO"

    # ---------- 数据库 ----------
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # ---------- Github API ----------
    github_token: str = ""
    github_api_base: str = "https://api.github.com"
    github_request_interval: float = 0.7
    # Search API 单独限流（认证用户 30 次/分钟），间隔需要更大一些
    github_search_interval: float = 2.2
    github_max_repos: int = 500
    github_search_pages: int = 5
    github_rate_limit_threshold: int = 50
    github_cache_ttl: int = 6 * 60 * 60  # 6 小时
    github_backfill_stargazers: bool = True
    github_backfill_limit: int = 30

    # 全网搜索：前端搜索框的远程检索（只读，不写库；关闭后仅检索本地库）
    github_remote_search_enabled: bool = True
    # 单次返回条数上限，控制 Search API 配额消耗（认证 30 次/分钟）
    github_remote_search_per_page: int = 10

    # ---------- 定时任务（UTC 小时）----------
    fetch_cron_hour: int = 0
    delta_cron_hour: int = 1
    cleanup_cron_hour: int = 19
    snapshot_retention_days: int = 90

    # ---------- 安全 / 其它 ----------
    admin_token: str = "change-me-please"
    # 管理接口是否允许「本机回环地址免 Token」：true 时 127.0.0.1/::1 可直接调用，
    # 公网部署必须设为 false 并继续使用 X-Admin-Token
    admin_allow_local: bool = True
    # 是否进一步放行内网地址（10/8、172.16/12、192.168/16）。
    # Docker 部署时容器看到的来源通常是网关地址（如 172.17.0.1），需要此项才能在页面上一键刷新；
    # 仅在服务不对外暴露时开启
    admin_allow_private: bool = False
    cors_origins: str = "*"
    demo_seed_on_empty: bool = True

    @property
    def web_dir(self) -> Path:
        """前端静态资源目录（web/index.html）。"""
        return BASE_DIR / "web"

    @property
    def data_dir(self) -> Path:
        """SQLite 数据目录。"""
        return BASE_DIR / "data"

    @property
    def cors_origin_list(self) -> list[str]:
        """把 CORS_ORIGINS 字符串解析成列表。"""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def db_path(self) -> Path:
        """从 DATABASE_URL 中解析出 SQLite 文件路径，用于自动创建目录。"""
        url = self.database_url
        prefix = "sqlite+aiosqlite:///"
        if url.startswith(prefix):
            return Path(url[len(prefix) :])
        return self.data_dir / "app.db"


@lru_cache
def get_settings() -> Settings:
    """单例获取配置（进程内缓存）。"""
    return Settings()


def settings_dict() -> dict[str, Any]:
    """导出可公开的配置字典（调试用，自动隐藏敏感字段）。"""
    data = get_settings().model_dump()
    for key in ("github_token", "admin_token"):
        if data.get(key):
            data[key] = "***"
    return data
