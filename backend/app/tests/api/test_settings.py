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
            email=f"set_{uid}@example.com",
            username=f"set_{uid}",
            hashed_password=hash_password("TestPass123!"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": f"set_{uid}",
            "password": "TestPass123!",
        },
    )
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


class TestSettingsEndpoint:
    async def test_settings_requires_auth(self, client):
        resp = await client.get("/api/v1/settings")
        assert resp.status_code in (401, 403)

    async def test_settings_update_requires_auth(self, client):
        resp = await client.put("/api/v1/settings", json={})
        assert resp.status_code in (401, 403)

    async def test_settings_returns_defaults(self, authed_client):
        resp = await authed_client.get("/api/v1/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"] == "dark"
        assert data["language"] == "en"
        assert data["notifications_enabled"] is True

    async def test_settings_update_persists(self, authed_client):
        resp = await authed_client.put("/api/v1/settings", json={"theme": "light"})
        assert resp.status_code == 200
        assert resp.json()["theme"] == "light"

        resp = await authed_client.get("/api/v1/settings")
        assert resp.json()["theme"] == "light"
