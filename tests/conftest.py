"""测试共享 fixture：建表 + 演示数据。"""

import pytest

from app.db.base import Base
from app.db.init_db import init_database
from app.db.session import AsyncSessionLocal, engine
from app.services.demo_seed import seed_demo_data_if_empty


@pytest.fixture(autouse=True)
async def setup_db():  # noqa: ANN201
    """每个测试用例开始时重建数据库并写入演示数据，结束时删除表。"""
    await init_database()
    async with AsyncSessionLocal() as session:
        await seed_demo_data_if_empty(session)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
