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
            email=f"res_{uid}@example.com",
            username=f"res_{uid}",
            hashed_password=hash_password("TestPass123!"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": f"res_{uid}",
            "password": "TestPass123!",
        },
    )
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


class TestResearchEndpoint:
    async def test_research_requires_auth(self, client):
        resp = await client.post("/api/v1/research/", json={"topic": "test"})
        assert resp.status_code in (401, 403)

    async def test_research_returns_response(self, authed_client):
        resp = await authed_client.post(
            "/api/v1/research/",
            json={
                "topic": "What is theft under BNS?",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic"] == "What is theft under BNS?"
        assert "summary" in data
        assert "findings" in data
        assert "citations" in data
        assert "generated_at" in data

    async def test_deep_research_requires_auth(self, client):
        resp = await client.post("/api/v1/research/deep", json={"topic": "test"})
        assert resp.status_code in (401, 403)
