"""Auth flow tests: register, login, refresh rotation, RBAC."""

from __future__ import annotations

from httpx import AsyncClient


async def test_register_then_login_roundtrip(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "username": "alice", "password": "Password1!"},
    )
    assert reg.status_code == 201
    body = reg.json()
    assert body["username"] == "alice"
    assert body["role"] == "user"
    assert body["is_superuser"] is False
    assert "password_hash" not in body
    assert "created_at" in body


async def test_login_returns_token_pair(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "username": "alice", "password": "Password1!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "Password1!"},
    )
    assert login.status_code == 200
    data = login.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


async def test_login_bad_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "username": "alice", "password": "Password1!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "wrong"},
    )
    assert login.status_code == 401
    assert login.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_refresh_rotation(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "username": "alice", "password": "Password1!"},
    )
    login = (
        await client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "Password1!"},
        )
    ).json()
    old_rt = login["refresh_token"]

    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
    assert refreshed.status_code == 200
    new_rt = refreshed.json()["refresh_token"]
    assert new_rt != old_rt

    # Old token must be replayed-rejected after rotation.
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
    assert replay.status_code == 401


async def test_me_endpoints(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "username": "alice", "password": "Password1!"},
    )
    login = (
        await client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "Password1!"},
        )
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    me_auth = await client.get("/api/v1/auth/me", headers=headers)
    assert me_auth.status_code == 200
    assert me_auth.json()["username"] == "alice"

    me_users = await client.get("/api/v1/users/me", headers=headers)
    assert me_users.status_code == 200
    assert me_users.json()["email"] == "a@b.com"


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


async def test_register_duplicate_username(client: AsyncClient) -> None:
    payload = {"email": "a@b.com", "username": "alice", "password": "Password1!"}
    await client.post("/api/v1/auth/register", json=payload)
    dup = await client.post("/api/v1/auth/register", json=payload)
    assert dup.status_code == 500


async def test_invalid_username_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "username": "bad name!", "password": "Password1!"},
    )
    assert resp.status_code == 422
