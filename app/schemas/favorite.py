"""收藏相关输入输出模型。"""

from pydantic import BaseModel, Field


class FavoriteCreate(BaseModel):
    """新增收藏请求体。"""

    repo_id: int = Field(..., description="Github 仓库 ID")


class FavoriteResult(BaseModel):
    """收藏操作结果。"""

    repo_id: int
    is_favorite: bool
    favorite_count: int = 0
