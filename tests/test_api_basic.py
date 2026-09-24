"""基础接口冒烟测试。"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """返回测试 HTTP 客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def test_health(client):
    """健康检查。"""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "ok"


async def test_list_repos(client):
    """榜单列表默认返回数据（演示数据会自动写入）。"""
    resp = await client.get("/api/v1/repos?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] > 0
    assert data["items"][0]["rank"] == 1


async def test_languages(client):
    """语言列表接口。"""
    resp = await client.get("/api/v1/languages")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


async def test_favorite_flow(client):
    """收藏增删查。"""
    headers = {"X-Client-Id": "pytest-client"}

    # 先取一个 repo_id
    resp = await client.get("/api/v1/repos?page=1&page_size=1")
    repo_id = resp.json()["data"]["items"][0]["repo_id"]

    # 新增收藏
    resp = await client.post("/api/v1/favorites", json={"repo_id": repo_id}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_favorite"] is True

    # 查看收藏列表
    resp = await client.get("/api/v1/favorites/ids", headers=headers)
    assert repo_id in resp.json()["data"]

    # 取消收藏
    resp = await client.delete(f"/api/v1/favorites/{repo_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_favorite"] is False
