import uuid

import pytest
import pytest_asyncio
from app.core.password import hash_password
from app.core.permissions import Role


@pytest_asyncio.fixture
async def admin_client(client):
    from app.database.models.user import User
    from app.database.session import async_session_factory

    uid = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email=f"admin_{uid}@example.com",
            username=f"admin_{uid}",
            hashed_password=hash_password("AdminPass123!"),
            role=Role.ADMIN.value,
            full_name="Test Admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": f"admin_{uid}",
            "password": "AdminPass123!",
        },
    )
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def user_client(client):
    from app.database.models.user import User
    from app.database.session import async_session_factory

    uid = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email=f"user_{uid}@example.com",
            username=f"user_{uid}",
            hashed_password=hash_password("UserPass123!"),
            role=Role.USER.value,
            full_name="Test User",
            is_active=True,
        )
        session.add(user)
        await session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": f"user_{uid}",
            "password": "UserPass123!",
        },
    )
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


class TestAdminAuth:
    async def test_admin_stats_requires_auth(self, client):
        resp = await client.get("/api/v1/admin/stats")
        assert resp.status_code in (401, 403)

    async def test_admin_stats_requires_admin_role(self, user_client):
        resp = await user_client.get("/api/v1/admin/stats")
        assert resp.status_code == 403

    async def test_admin_audit_logs_requires_auth(self, client):
        resp = await client.get("/api/v1/admin/audit-logs")
        assert resp.status_code in (401, 403)

    async def test_admin_audit_logs_requires_admin_role(self, user_client):
        resp = await user_client.get("/api/v1/admin/audit-logs")
        assert resp.status_code == 403


class TestAdminStats:
    async def test_admin_stats_returns_counts(self, admin_client):
        resp = await admin_client.get("/api/v1/admin/stats")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("users", "chats", "messages", "documents", "uploads", "ingested_docs", "pending_ingestions"):
            assert key in data
            assert isinstance(data[key], int)


class TestAdminAuditLogs:
    async def test_audit_logs_returns_paginated(self, admin_client):
        resp = await admin_client.get("/api/v1/admin/audit-logs")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "logs" in data
        assert "limit" in data
        assert "offset" in data

    async def test_audit_logs_respects_limit(self, admin_client):
        resp = await admin_client.get("/api/v1/admin/audit-logs?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5


class TestAdminPromptsAuth:
    async def test_create_prompt_requires_admin(self, user_client):
        resp = await user_client.post(
            "/api/v1/admin/prompts",
            json={
                "name": "test-prompt",
                "category": "test",
                "content": "hello",
            },
        )
        assert resp.status_code == 403

    async def test_list_prompts_requires_admin(self, user_client):
        resp = await user_client.get("/api/v1/admin/prompts")
        assert resp.status_code == 403

    async def test_get_prompt_requires_admin(self, user_client):
        resp = await user_client.get("/api/v1/admin/prompts/does-not-exist")
        assert resp.status_code == 403

    async def test_get_prompt_by_name_requires_admin(self, user_client):
        resp = await user_client.get("/api/v1/admin/prompts/by-name/foo")
        assert resp.status_code == 403

    async def test_update_prompt_requires_admin(self, user_client):
        resp = await user_client.patch("/api/v1/admin/prompts/does-not-exist", json={})
        assert resp.status_code == 403

    async def test_manage_versions_requires_admin(self, user_client):
        resp = await user_client.get("/api/v1/admin/prompts/nonexistent/versions")
        assert resp.status_code == 403


class TestAdminPromptsCRUD:
    @pytest.fixture
    def prompt_data(self):
        suffix = uuid.uuid4().hex[:8]
        return {"name": f"prompt-{suffix}", "category": "legal", "content": "You are a legal assistant."}

    async def test_create_and_list_prompt(self, admin_client, prompt_data):
        resp = await admin_client.post("/api/v1/admin/prompts", json=prompt_data)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == prompt_data["name"]
        assert data["category"] == prompt_data["category"]
        assert data["current_version"] == 1
        prompt_id = data["id"]

        resp = await admin_client.get("/api/v1/admin/prompts")
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert prompt_data["name"] in names

        resp = await admin_client.get(f"/api/v1/admin/prompts/{prompt_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == prompt_data["name"]

        resp = await admin_client.get(f"/api/v1/admin/prompts/by-name/{prompt_data['name']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == prompt_data["name"]

    async def test_create_duplicate_name(self, admin_client, prompt_data):
        await admin_client.post("/api/v1/admin/prompts", json=prompt_data)
        resp = await admin_client.post("/api/v1/admin/prompts", json=prompt_data)
        assert resp.status_code == 400

    async def test_update_prompt_content_creates_new_version(self, admin_client, prompt_data):
        resp = await admin_client.post("/api/v1/admin/prompts", json=prompt_data)
        prompt_id = resp.json()["id"]

        resp = await admin_client.patch(
            f"/api/v1/admin/prompts/{prompt_id}",
            json={
                "content": "Updated content",
                "changelog": "Second version",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["current_version"] == 2

    async def test_get_nonexistent_prompt_returns_404(self, admin_client):
        resp = await admin_client.get("/api/v1/admin/prompts/does-not-exist")
        assert resp.status_code == 404

    async def test_get_nonexistent_prompt_by_name_returns_404(self, admin_client):
        resp = await admin_client.get("/api/v1/admin/prompts/by-name/nonexistent")
        assert resp.status_code == 404

    async def test_filter_prompts_by_category(self, admin_client):
        await admin_client.post(
            "/api/v1/admin/prompts",
            json={
                "name": "cat-a",
                "category": "a",
                "content": "x",
            },
        )
        await admin_client.post(
            "/api/v1/admin/prompts",
            json={
                "name": "cat-b",
                "category": "b",
                "content": "y",
            },
        )
        resp = await admin_client.get("/api/v1/admin/prompts?category=a")
        names = [p["name"] for p in resp.json()]
        assert "cat-a" in names
        assert "cat-b" not in names


class TestAdminPromptVersions:
    async def test_create_and_list_versions(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/admin/prompts",
            json={
                "name": "versioned-prompt",
                "category": "test",
                "content": "v1 content",
            },
        )
        prompt_id = resp.json()["id"]

        resp = await admin_client.post(
            f"/api/v1/admin/prompts/{prompt_id}/versions",
            params={"content": "v2 content", "changelog": "Second version"},
        )
        assert resp.status_code == 201
        assert resp.json()["version"] == 2

        resp = await admin_client.get(f"/api/v1/admin/prompts/{prompt_id}/versions")
        assert resp.status_code == 200
        versions = resp.json()
        assert len(versions) == 2
        assert versions[0]["version"] == 2
        assert versions[1]["version"] == 1

    async def test_activate_version(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/admin/prompts",
            json={
                "name": "activate-test",
                "category": "test",
                "content": "v1",
            },
        )
        prompt_id = resp.json()["id"]

        await admin_client.post(
            f"/api/v1/admin/prompts/{prompt_id}/versions",
            params={"content": "v2", "changelog": "v2"},
        )
        await admin_client.post(
            f"/api/v1/admin/prompts/{prompt_id}/versions",
            json={"content": "v3", "changelog": "v3"},
        )

        resp = await admin_client.post(
            f"/api/v1/admin/prompts/{prompt_id}/activate",
            json={"version": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == 1

        resp = await admin_client.get(f"/api/v1/admin/prompts/{prompt_id}")
        assert resp.json()["current_version"] == 1

    async def test_activate_nonexistent_version_returns_404(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/admin/prompts",
            json={
                "name": "activate-404",
                "category": "test",
                "content": "v1",
            },
        )
        prompt_id = resp.json()["id"]
        resp = await admin_client.post(
            f"/api/v1/admin/prompts/{prompt_id}/activate",
            json={"version": 99},
        )
        assert resp.status_code == 404

    async def test_get_prompt_by_name_with_version(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/admin/prompts",
            json={
                "name": "by-name-version",
                "category": "test",
                "content": "v1",
            },
        )
        await admin_client.post(
            f"/api/v1/admin/prompts/{resp.json()['id']}/versions",
            params={"content": "v2", "changelog": "v2"},
        )
        resp = await admin_client.get("/api/v1/admin/prompts/by-name/by-name-version?version=2")
        assert resp.status_code == 200
        assert resp.json()["name"] == "by-name-version"
        versions = {v["version"]: v for v in resp.json()["versions"]}
        assert 2 in versions
        assert versions[2]["content"] == "v2"

    async def test_delete_version(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/admin/prompts",
            json={
                "name": "delete-version",
                "category": "test",
                "content": "v1",
            },
        )
        prompt_id = resp.json()["id"]
        await admin_client.post(
            f"/api/v1/admin/prompts/{prompt_id}/versions",
            params={"content": "v2", "changelog": "v2"},
        )

        resp = await admin_client.delete(f"/api/v1/admin/prompts/{prompt_id}/versions/1")
        assert resp.status_code in (200, 400)

    async def test_delete_active_version_returns_400(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/admin/prompts",
            json={
                "name": "delete-active",
                "category": "test",
                "content": "v1",
            },
        )
        prompt_id = resp.json()["id"]
        resp = await admin_client.delete(f"/api/v1/admin/prompts/{prompt_id}/versions/1")
        assert resp.status_code == 400
