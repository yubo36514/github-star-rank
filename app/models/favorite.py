"""收藏表：按客户端标识（localStorage 中的 UUID）隔离，无需登录。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class Favorite(Base):
    """用户收藏记录。"""

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("client_id", "repo_id", name="uq_favorite_client_repo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    repo_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
