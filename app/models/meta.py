"""元数据表：KV 配置、调度锁、Github API 响应缓存。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class MetaInfo(Base):
    """KV 元数据，如最近抓取时间、Github 配额剩余等。"""

    __tablename__ = "meta_info"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )


class SchedulerLock(Base):
    """定时任务锁，防止任务并发执行（异常退出时靠 expires_at 自动释放）。"""

    __tablename__ = "scheduler_lock"

    task_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class ApiCache(Base):
    """Github API 响应缓存，减少对官方接口的重复请求。"""

    __tablename__ = "api_cache"

    cache_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON 字符串
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # Unix 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
