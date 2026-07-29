import uuid

import pytest_asyncio
from app.core.password import hash_password


@pytest_asyncio.fixture
async def authed_client(client):
    from app.database.models.user import User
    from app.database.session import async_session_factory

    uid = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email=f"dash_{uid}@example.com",
            username=f"dash_{uid}",
            hashed_password=hash_password("TestPass123!"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": f"dash_{uid}",
            "password": "TestPass123!",
        },
    )
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


class TestDashboardEndpoint:
    async def test_dashboard_requires_auth(self, client):
        resp = await client.get("/api/v1/dashboard/")
        assert resp.status_code in (401, 403)

    async def test_dashboard_returns_stats(self, authed_client):
        resp = await authed_client.get("/api/v1/dashboard/")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("chats", "documents", "messages", "uploads"):
            assert key in data
            assert isinstance(data[key], int)
