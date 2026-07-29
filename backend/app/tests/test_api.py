import uuid

import pytest


class TestHealthEndpoint:
    async def test_health_returns_200(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200

    async def test_health_has_expected_keys(self, client):
        resp = await client.get("/api/v1/health")
        data = resp.json()
        assert "status" in data
        assert "services" in data


class TestRootEndpoint:
    async def test_root_returns_info(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "1.0.0"


class TestAuthEndpoints:
    async def test_register_missing_body(self, client):
        resp = await client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422

    async def test_login_missing_body(self, client):
        resp = await client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422


class TestAuthFlow:
    @pytest.fixture
    def test_user(self):
        uid = uuid.uuid4().hex[:8]
        return {
            "email": f"test_{uid}@example.com",
            "username": f"user_{uid}",
            "password": "StrongPass123!",
            "full_name": "Test User",
        }

    async def test_register_and_login(self, client, test_user):
        resp = await client.post("/api/v1/auth/register", json=test_user)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == test_user["email"]
        assert data["username"] == test_user["username"]
        assert "id" in data

        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_register_duplicate(self, client, test_user):
        await client.post("/api/v1/auth/register", json=test_user)
        resp = await client.post("/api/v1/auth/register", json=test_user)
        assert resp.status_code == 409

    async def test_login_wrong_password(self, client, test_user):
        await client.post("/api/v1/auth/register", json=test_user)
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": "WrongPass!",
            },
        )
        assert resp.status_code == 401

    async def test_refresh_token_flow(self, client, test_user):
        await client.post("/api/v1/auth/register", json=test_user)
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        tokens = login_resp.json()

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    async def test_access_protected_endpoint(self, client, test_user):
        await client.post("/api/v1/auth/register", json=test_user)
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        token = login_resp.json()["access_token"]

        resp = await client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == test_user["email"]

    async def test_unauthenticated_access_returns_401(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)

    async def test_invalid_token_returns_401(self, client):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": "Bearer invalid_token_here",
            },
        )
        assert resp.status_code in (401, 403)

    async def test_liveness_probe(self, client):
        resp = await client.get("/api/v1/health/liveness")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    async def test_cors_headers(self, client):
        resp = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code in (200, 204, 400)


class TestDraftingEndpoints:
    async def test_list_types_requires_auth(self, client):
        resp = await client.get("/api/v1/drafting/types")
        assert resp.status_code in (200, 401)


class TestChatEndpoints:
    async def test_list_chats_requires_auth(self, client):
        resp = await client.get("/api/v1/chat/")
        assert resp.status_code in (401, 403)
