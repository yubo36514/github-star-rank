"""数据访问层统一导出。"""

from app.repositories import favorite_repo, meta_repo, repo_repo, snapshot_repo

__all__ = ["repo_repo", "snapshot_repo", "favorite_repo", "meta_repo"]
