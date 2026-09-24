"""每日快照表：记录每个仓库每天的 Star 数，用于计算 7 日增量。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class RepoSnapshot(Base):
    """仓库每日快照（一个仓库一天一条，重复写入时更新）。"""

    __tablename__ = "repo_snapshots"
    __table_args__ = (UniqueConstraint("repo_id", "snapshot_date", name="uq_snapshot_repo_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    snapshot_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    total_stars: Mapped[int] = mapped_column(Integer, nullable=False)
    forks_count: Mapped[int] = mapped_column(Integer, default=0)
    open_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    delta_stars: Mapped[int] = mapped_column(Integer, default=0)  # 相对上一快照的增量
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Snapshot repo={self.repo_id} {self.snapshot_date} stars={self.total_stars}>"
