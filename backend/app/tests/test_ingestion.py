"""Phase 4 ingestion tests: extraction, cleaning, structure, chunking, persistence."""

from __future__ import annotations

import uuid

import pytest
from app.core.exceptions import DocumentProcessingFailedError, IngestionFailedError
from app.ingestion.chunker import chunk_document
from app.ingestion.cleaner import clean_text, normalize_whitespace
from app.ingestion.extractor import extract_text
from app.ingestion.pipeline import get_latest_version_for_document, run_ingestion
from app.ingestion.structure import detect_structure
from app.models.chunks import DocumentChunk
from app.models.sources import IngestionJob, LegalSource, SourceDocument
from app.models.user import User
from app.source_management.service import create_uploaded_document
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SAMPLE_ACT = """CHAPTER I
PRELIMINARY
1. Short title.
(1) This Act may be called the Bharatiya Nyaya Sanhita, 2023.
(2) It shall come into force on such date as the Central Government may appoint.
2. Definitions.
In this Sanhita, unless the context otherwise requires,—
(a) "act" denotes a series of acts;
Explanation.—The word "offence" denotes a thing made punishable by this Sanhita.
3. Punishment.
Whoever commits any offence shall be punished according to this Sanhita.
Illustration 1.—A kills B, which is murder.
Exception.—Nothing is an offence which is done in the exercise of the right of private defence.
"""


@pytest.mark.parametrize(
    ("extension", "kind"),
    [(".txt", "text/plain")],
)
def test_extract_text_txt(tmp_path, extension, kind) -> None:
    p = tmp_path / f"src{extension}"
    p.write_text("hello\nworld", encoding="utf-8")
    assert extract_text(p) == "hello\nworld"


def test_extract_text_unsupported(tmp_path) -> None:
    p = tmp_path / "x.exe"
    p.write_bytes(b"MZ")
    with pytest.raises(DocumentProcessingFailedError):
        extract_text(p)


def test_extract_text_missing(tmp_path) -> None:
    with pytest.raises(DocumentProcessingFailedError):
        extract_text(tmp_path / "nope.pdf")


def test_clean_text_collapses_blank_lines() -> None:
    raw = "Section 1.\n\n\n\n\nWhoever commits theft.\n\n"
    cleaned = clean_text(raw)
    assert "\n\n\n" not in cleaned
    assert cleaned.startswith("Section 1.")


def test_clean_text_removes_artifact_lines() -> None:
    raw = "1. Section text.\n\u2022\u2022\u2022\n\uf0b7\uf0b7\n2. Next section.\n"
    cleaned = clean_text(raw)
    assert "\u2022" not in cleaned
    assert "\uf0b7" not in cleaned


def test_clean_text_removes_standalone_page_numbers() -> None:
    raw = "1. Text.\n\n358\n\n2. More.\n"
    cleaned = clean_text(raw)
    assert "\n358\n" not in cleaned


def test_normalize_whitespace() -> None:
    assert normalize_whitespace("a   b\t\tc") == "a b c"


def test_detect_structure_finds_sections_and_elements() -> None:
    els = detect_structure(clean_text(SAMPLE_ACT))
    sections = [e for e in els if e.element_type == "SECTION"]
    assert [s.section_num for s in sections] == ["1", "2", "3"]
    kinds = {e.element_type for e in els}
    assert {"EXPLANATION", "ILLUSTRATION", "EXCEPTION"} <= kinds
    # Chapter context propagates to sections.
    sec2 = next(e for e in sections if e.section_num == "2")
    assert sec2.chapter == "I"
    assert sec2.chapter_title == "PRELIMINARY"


def test_detect_structure_ignores_signature_blob() -> None:
    raw = clean_text("1. A.\n" + "2.5.4.20=e8b886a9336825f4d863\n" + "3. B.\n")
    els = detect_structure(raw)
    sections = [e.section_num for e in els if e.element_type == "SECTION"]
    assert sections == ["1", "3"]


def test_chunk_document_parents_and_children() -> None:
    els = detect_structure(clean_text(SAMPLE_ACT))
    chunks = chunk_document(els)
    parents = [c for c in chunks if c.is_parent]
    children = [c for c in chunks if not c.is_parent]
    assert len(parents) == 3
    # Section 2 should have an Explanation child.
    expl_children = [c for c in children if c.element_type == "EXPLANATION"]
    assert len(expl_children) >= 1
    assert expl_children[0].parent_text is not None
    assert expl_children[0].section_num == "2"
    # Hashes are unique and stable.
    hashes = {c.content_hash for c in chunks}
    assert len(hashes) == len(chunks)


def test_chunk_document_full_pdf() -> None:
    """End-to-end over the real BNS.pdf fixture if present."""
    from pathlib import Path

    pdf = Path(__file__).resolve().parents[3] / "BNS.pdf"
    if not pdf.exists():
        pytest.skip("BNS.pdf not available in repo root")
    raw = extract_text(pdf)
    cleaned = clean_text(raw)
    els = detect_structure(cleaned)
    sections = [e for e in els if e.element_type == "SECTION"]
    assert len(sections) >= 350
    assert sections[0].section_num == "1"
    assert sections[-1].section_num == "358"
    chunks = chunk_document(els)
    assert len(chunks) >= 400


async def _user(session: AsyncSession, username: str) -> User:
    u = User(email=f"{username}@b.com", username=username, password_hash="x", role="USER")
    session.add(u)
    await session.flush()
    return u


async def test_run_ingestion_persists_chunks(db_session: AsyncSession, tmp_path) -> None:
    user = await _user(db_session, "ingest_actor")
    upload = await create_uploaded_document(
        db_session,
        filename="act.txt",
        file_type="txt",
        file_size=len(SAMPLE_ACT.encode()),
        content=SAMPLE_ACT.encode("utf-8"),
        uploaded_by=user.id,
    )
    assert not upload.is_duplicate
    doc = upload.document
    version = await get_latest_version_for_document(db_session, doc)

    job_id = uuid.uuid4()
    job = IngestionJob(document_id=doc.id, status="pending", progress=0, chunks_count=0)
    job.id = job_id
    db_session.add(job)
    await db_session.flush()

    ingest = await run_ingestion(db_session, job, doc, source_version=version)
    assert ingest.sections_count == 3
    assert ingest.chunks_count >= 6
    assert job.status == "completed"
    assert job.chunks_count == ingest.chunks_count

    rows = (await db_session.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id))).scalars().all()
    assert len(rows) == ingest.chunks_count
    parents = [r for r in rows if r.element_type == "SECTION"]
    assert len(parents) == 3
    # Children reference the parent chunk.
    expl = next(r for r in rows if r.element_type == "EXPLANATION")
    assert expl.parent_chunk_id is not None
    parent = next(r for r in rows if r.id == expl.parent_chunk_id)
    assert parent.element_type == "SECTION"


async def test_run_ingestion_missing_file_fails(db_session: AsyncSession, tmp_path) -> None:
    user = await _user(db_session, "ingest_fail")
    result = await create_uploaded_document(
        db_session,
        filename="ghost.pdf",
        file_type="pdf",
        file_size=4,
        content=b"data",
        uploaded_by=user.id,
    )
    doc = result.document
    version = await get_latest_version_for_document(db_session, doc)
    # Remove the file so extraction fails.
    import os

    os.remove(doc.stored_path)

    job = IngestionJob(document_id=doc.id, status="pending", progress=0, chunks_count=0)
    db_session.add(job)
    await db_session.flush()

    with pytest.raises(IngestionFailedError):
        await run_ingestion(db_session, job, doc, source_version=version)
    assert job.status == "failed"
    assert job.error_message is not None

    rows = (await db_session.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id))).scalars().all()
    assert rows == []


async def test_ingest_endpoint_completes(client: AsyncClient, db_session: AsyncSession) -> None:
    """Full HTTP flow: upload a legal text file then ingest it."""
    from app.tests.test_sources import _register_and_login

    headers = await _register_and_login(client, db_session, "e2e_ingest")
    up = (
        await client.post(
            "/api/v1/upload/",
            files={"file": ("act.txt", SAMPLE_ACT.encode("utf-8"), "text/plain")},
            headers=headers,
        )
    ).json()
    job = (
        await client.post(
            f"/api/v1/ingestion/ingest/{up['id']}",
            headers=headers,
        )
    ).json()
    assert job["status"] == "completed"
    assert job["chunks_count"] >= 6
    assert job["stats"]["sections"] == 3

    # The source should now be PROCESSED.
    doc = (
        await db_session.execute(select(SourceDocument).where(SourceDocument.id == uuid.UUID(up["id"])))
    ).scalar_one()
    source = (await db_session.execute(select(LegalSource).where(LegalSource.id == doc.source_id))).scalar_one()
    assert source.status == "PROCESSED"
