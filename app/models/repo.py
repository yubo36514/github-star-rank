"""仓库主表：保存仓库的最新状态与 7 日增量指标。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class Repo(Base):
    """Github 仓库（榜单主体）。"""

    __tablename__ = "repos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Github 仓库唯一 ID（全站唯一，作为业务主键使用）
    repo_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    # 主编程语言；无语言时统一存 "Unknown"，便于筛选
    language: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    html_url: Mapped[str] = mapped_column(String(512), nullable=False)
    homepage: Mapped[str | None] = mapped_column(String(512), default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(512), default=None)
    topics: Mapped[str | None] = mapped_column(Text, default=None)  # JSON 数组字符串
    license: Mapped[str | None] = mapped_column(String(120), default=None)

    total_stars: Mapped[int] = mapped_column(Integer, default=0, index=True)
    forks_count: Mapped[int] = mapped_column(Integer, default=0)
    open_issues_count: Mapped[int] = mapped_column(Integer, default=0)

    # 近 1 日 / 近 7 日新增 Star，以及 7 日增长率
    stars_1d: Mapped[int] = mapped_column(Integer, default=0)
    stars_7d: Mapped[int] = mapped_column(Integer, default=0, index=True)
    stars_7d_rate: Mapped[float] = mapped_column(default=0.0)
    # True 表示 7 日增量是「估算值」（历史快照不足 7 天）
    is_partial: Mapped[bool] = mapped_column(Boolean, default=False)

    repo_created_at: Mapped[str | None] = mapped_column(String(32), default=None)
    pushed_at: Mapped[str | None] = mapped_column(String(32), default=None)

    # 是否继续跟踪（False 时定时任务不再抓取）
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Repo {self.full_name} stars={self.total_stars} +7d={self.stars_7d}>"
