"""Source management tests: upload, documents, ingestion jobs, RBAC."""

from __future__ import annotations

from app.core.constants import SOURCE_INACTIVE, SOURCE_PENDING_PROCESSING, SOURCE_UPLOADED
from app.models.sources import LegalSource
from app.models.user import User
from app.source_management.service import create_uploaded_document, update_source_status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _register_and_login(client: AsyncClient, session: AsyncSession, username: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": f"{username}@b.com", "username": username, "password": "Password1!"},
    )
    # Grant upload permission by promoting to superuser (bypasses RBAC check).
    user = (await session.execute(select(User).where(User.username == username))).scalar_one()
    user.is_superuser = True
    await session.flush()
    await session.commit()
    login = (
        await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "Password1!"},
        )
    ).json()
    return {"Authorization": f"Bearer {login['access_token']}"}


async def _make_user(session: AsyncSession, username: str) -> User:
    user = User(
        email=f"{username}@b.com",
        username=username,
        password_hash="x",
        role="USER",
    )
    session.add(user)
    await session.flush()
    return user


async def test_upload_document(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _register_and_login(client, db_session, "admin_upload")
    resp = await client.post(
        "/api/v1/upload/",
        files={"file": ("bns.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "bns.pdf"
    assert data["status"] == "uploaded"
    assert data["is_duplicate"] is False
    assert data["id"]


async def test_upload_requires_auth(client: AsyncClient, db_session: AsyncSession) -> None:
    resp = await client.post(
        "/api/v1/upload/",
        files={"file": ("bns.pdf", b"%PDF", "application/pdf")},
    )
    assert resp.status_code == 401


async def test_upload_rejects_bad_extension(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _register_and_login(client, db_session, "admin_ext")
    resp = await client.post(
        "/api/v1/upload/",
        files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_list_documents(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _register_and_login(client, db_session, "admin_list")
    await client.post(
        "/api/v1/upload/",
        files={"file": ("a.txt", b"hello world", "text/plain")},
        headers=headers,
    )
    resp = await client.get("/api/v1/documents/", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["documents"][0]["filename"] == "a.txt"


async def test_delete_document(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _register_and_login(client, db_session, "admin_del")
    up = (
        await client.post(
            "/api/v1/upload/",
            files={"file": ("c.txt", b"data", "text/plain")},
            headers=headers,
        )
    ).json()
    resp = await client.delete(f"/api/v1/documents/{up['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_start_ingestion_job(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _register_and_login(client, db_session, "admin_ingest")
    bns_text = (
        "CHAPTER I\nPRELIMINARY\n"
        "1. Short title.\n(1) This Act may be called the Bharatiya Nyaya Sanhita, 2023.\n"
        "2. Definitions.\nExplanation.—In this Sanhita the following expressions have meanings.\n"
        "3. Punishment.\nWhoever commits an offence shall be punished accordingly.\n"
    )
    up = (
        await client.post(
            "/api/v1/upload/",
            files={"file": ("d.txt", bns_text.encode("utf-8"), "text/plain")},
            headers=headers,
        )
    ).json()
    job = await client.post(
        f"/api/v1/ingestion/ingest/{up['id']}?chunk_strategy=recursive",
        headers=headers,
    )
    assert job.status_code == 200
    body = job.json()
    assert body["status"] == "completed"
    assert body["filename"] == "d.txt"
    assert body["chunks_count"] >= 3
    assert body["stats"]["sections"] >= 3


async def test_list_ingestion_jobs(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _register_and_login(client, db_session, "admin_jobs")
    up = (
        await client.post(
            "/api/v1/upload/",
            files={"file": ("e.txt", b"data", "text/plain")},
            headers=headers,
        )
    ).json()
    await client.post(f"/api/v1/ingestion/ingest/{up['id']}", headers=headers)
    resp = await client.get("/api/v1/ingestion/jobs", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["jobs"]


async def test_source_state_machine(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "sm_actor")
    result = await create_uploaded_document(
        db_session,
        filename="law.txt",
        file_type="txt",
        file_size=4,
        content=b"data",
        uploaded_by=user.id,
    )
    src = result.document
    legal_source = (await db_session.execute(select(LegalSource).where(LegalSource.id == src.source_id))).scalar_one()
    assert legal_source.status == SOURCE_UPLOADED

    await update_source_status(db_session, legal_source, SOURCE_PENDING_PROCESSING)
    assert legal_source.status == SOURCE_PENDING_PROCESSING

    # UPLOADED/PENDING_PROCESSING -> INACTIVE is legal.
    await update_source_status(db_session, legal_source, SOURCE_INACTIVE)
    assert legal_source.status == SOURCE_INACTIVE


async def test_illegal_source_transition_rejected(client: AsyncClient, db_session: AsyncSession) -> None:
    from app.core.exceptions import InvalidRequestError

    user = await _make_user(db_session, "illegal_actor")
    result = await create_uploaded_document(
        db_session,
        filename="law2.txt",
        file_type="txt",
        file_size=4,
        content=b"more",
        uploaded_by=user.id,
    )
    legal_source = (
        await db_session.execute(select(LegalSource).where(LegalSource.id == result.document.source_id))
    ).scalar_one()
    # UPLOADED -> PENDING_REVIEW is not a valid transition.
    try:
        await update_source_status(db_session, legal_source, "PENDING_REVIEW")
        assert False, "expected InvalidRequestError"
    except InvalidRequestError:
        assert legal_source.status == SOURCE_UPLOADED
