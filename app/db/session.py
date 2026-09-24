"""异步数据库引擎与会话管理（SQLAlchemy 2.0 + aiosqlite）。"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()


def _ensure_parent_dir(url: str) -> None:
    """确保 SQLite 文件所在目录存在（相对路径以项目根目录为基准）。"""
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return
    raw = url[len(prefix) :]
    # Windows 绝对路径可能形如 /D:/xxx，这里去掉开头的斜杠
    if len(raw) > 2 and raw[0] == "/" and raw[2] == ":":
        raw = raw[1:]
    path = Path(raw)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


_ensure_parent_dir(settings.database_url)

# NullPool：SQLite 连接创建成本极低，用完即弃可避免多任务共享连接带来的锁竞争
engine = create_async_engine(
    settings.database_url,
    echo=False,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
    future=True,
)

# expire_on_commit=False：提交后仍可访问已加载的属性，便于序列化返回
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@event.listens_for(Engine, "connect")
def _sqlite_pragma(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
    """每个新连接建立时设置 SQLite PRAGMA：WAL 模式 + 忙等待，提升并发与可靠性。"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=8000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：为每个请求提供一个独立会话。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
