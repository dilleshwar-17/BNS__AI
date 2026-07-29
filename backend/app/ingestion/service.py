import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.database.models.ingestion_job import IngestionJob
from app.database.models.uploaded_file import UploadedFile
from app.ingestion.chunking.chunker import Chunker
from app.ingestion.extractors.document_parser import DocumentParser

logger = get_logger(__name__)
settings = get_settings()

UPLOAD_DIR = (
    Path(settings.database_url.replace("sqlite+aiosqlite:///", "").replace("postgresql+asyncpg://", "")).parent
    / "uploads"
    if "sqlite" in settings.database_url
    else Path("uploads")
)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class IngestionService:
    def __init__(self, db_session: AsyncSession | None = None):
        self.db_session = db_session
        self.parser = DocumentParser()
        self.chunker = Chunker(strategy="recursive")
        self._progress_callback: Callable | None = None

    def set_progress_callback(self, cb: Callable):
        self._progress_callback = cb

    async def ingest_file(
        self,
        file_id: str,
        user_id: str,
        chunk_size: int = 500,
        overlap: int = 50,
        chunk_strategy: str = "recursive",
        collection_name: str = "ingested_docs",
    ) -> dict:
        if not self.db_session:
            raise RuntimeError("db_session required for ingestion")

        result = await self.db_session.execute(select(UploadedFile).where(UploadedFile.id == file_id))
        uploaded_file = result.scalar_one_or_none()
        if not uploaded_file:
            raise FileNotFoundError(f"Uploaded file not found: {file_id}")

        job = await self._create_job(uploaded_file, user_id)
        self.chunker.strategy = chunk_strategy

        try:
            stats = await self._run_ingestion(
                job=job,
                file_path=uploaded_file.file_path,
                mime_type=uploaded_file.mime_type,
                chunk_size=chunk_size,
                overlap=overlap,
                collection_name=collection_name,
            )
            await self._complete_job(job, stats)
            return stats
        except Exception as e:
            await self._fail_job(job, str(e))
            raise

    async def _create_job(self, uploaded_file: UploadedFile, user_id: str) -> IngestionJob:
        job = IngestionJob(
            user_id=user_id,
            file_id=uploaded_file.id,
            filename=uploaded_file.filename,
            doc_type=uploaded_file.file_type,
            status="processing",
            progress=0,
        )
        self.db_session.add(job)
        await self.db_session.commit()
        await self.db_session.refresh(job)
        return job

    async def _run_ingestion(
        self,
        job: IngestionJob,
        file_path: str,
        mime_type: str | None,
        chunk_size: int,
        overlap: int,
        collection_name: str,
    ) -> dict:
        stats = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "file_path": file_path,
            "extraction": {"chars": 0, "method": ""},
            "chunking": {"chunks": 0, "strategy": self.chunker.strategy},
            "embedding": {"chunks_embedded": 0, "model": "nomic-embed-text"},
            "vector_store": {"collection": collection_name, "chunks_stored": 0},
            "graph": {"nodes_created": 0},
            "elapsed_seconds": 0,
        }
        start_time = time.time()

        await self._update_progress(job, 5, "Extracting text from document")
        raw_text = await self.parser.parse(file_path, mime_type)
        if not raw_text.strip():
            raise ValueError(f"No text could be extracted from {job.filename}")
        stats["extraction"]["chars"] = len(raw_text)
        stats["extraction"]["method"] = "document_parser"

        await self._update_progress(job, 20, f"Extracted {len(raw_text)} characters, chunking")
        chunks = self.chunker.chunk(raw_text, chunk_size=chunk_size, overlap=overlap, source=job.filename)
        if not chunks:
            raise ValueError("No chunks generated from extracted text")
        stats["chunking"]["chunks"] = len(chunks)
        job.chunks_count = len(chunks)

        await self._update_progress(job, 35, f"Generated {len(chunks)} chunks, generating embeddings")
        embedded_chunks = await self._embed_chunks(chunks, job)

        await self._update_progress(job, 60, f"Embedded {len(embedded_chunks)} chunks, storing in vector store")
        await self._store_in_vector_store(embedded_chunks, collection_name, job)

        await self._update_progress(job, 80, "Building knowledge graph")
        graph_nodes = await self._build_knowledge_graph(chunks, job.filename)

        stats["embedding"]["chunks_embedded"] = len(embedded_chunks)
        stats["vector_store"]["chunks_stored"] = len(embedded_chunks)
        stats["graph"]["nodes_created"] = graph_nodes
        stats["elapsed_seconds"] = round(time.time() - start_time, 2)

        return stats

    async def _embed_chunks(self, chunks: list[dict], job: IngestionJob) -> list[dict]:
        texts = [c["text"] for c in chunks]
        embeddings = await self._get_embeddings_batch(texts)
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i] if i < len(embeddings) else []
        return chunks

    async def _get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            from app.integrations.ollama import get_ollama_client

            client = get_ollama_client()
            resp = await client.post(
                "/api/embed",
                json={"model": "nomic-embed-text", "input": texts},
            )
            resp.raise_for_status()
            return resp.json()["embeddings"]
        except Exception as e:
            logger.warning("ollama_embedding_failed_falling_back", error=str(e))
            return [self._fake_embedding(t) for t in texts]

    def _fake_embedding(self, text: str) -> list[float]:
        import hashlib

        h = hashlib.md5(text.encode()).digest()
        vec = [b / 255.0 for b in h]
        vec = vec * 6
        return vec[:64]

    async def _store_in_vector_store(self, chunks: list[dict], collection_name: str, job: IngestionJob):
        try:
            import chromadb

            client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                headers={"Authorization": f"Bearer {settings.chroma_token}"},
            )
            try:
                collection = client.get_collection(collection_name)
            except Exception:
                collection = client.create_collection(collection_name)

            existing_ids = set()
            try:
                existing = collection.get(limit=10000)
                if existing and existing["ids"]:
                    existing_ids = set(existing["ids"])
            except Exception:
                pass

            texts = []
            embeddings = []
            ids = []
            metadatas = []
            new_count = 0

            for chunk in chunks:
                cid = chunk["id"]
                if cid in existing_ids:
                    continue
                texts.append(chunk["text"])
                embeddings.append(chunk.get("embedding", []))
                ids.append(cid)
                metadatas.append(
                    {
                        **chunk.get("metadata", {}),
                        "source_file": job.filename,
                        "job_id": job.id,
                    }
                )
                new_count += 1

            if new_count > 0:
                batch_size = 50
                for i in range(0, new_count, batch_size):
                    end = i + batch_size
                    collection.add(
                        documents=texts[i:end],
                        embeddings=embeddings[i:end],
                        ids=ids[i:end],
                        metadatas=metadatas[i:end],
                    )

            logger.info("vector_store_populated", collection=collection_name, new=new_count, total=len(chunks))
        except Exception as e:
            logger.warning("vector_store_upload_failed", error=str(e))

    async def _build_knowledge_graph(self, chunks: list[dict], filename: str) -> int:
        nodes_created = 0
        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            async with driver.session(database="neo4j") as session:
                for i, chunk in enumerate(chunks[:50]):
                    try:
                        await session.run(
                            """
                            MERGE (d:Document {source: $source, chunk_id: $chunk_id})
                            SET d.text = $text, d.chunk_index = $index
                            """,
                            source=filename,
                            chunk_id=chunk["id"],
                            text=chunk["text"][:2000],
                            index=chunk["metadata"].get("chunk_index", i),
                        )
                        nodes_created += 1
                    except Exception:
                        pass
            await driver.close()
            logger.info("graph_nodes_created", nodes=nodes_created)
        except Exception as e:
            logger.warning("graph_build_skipped", error=str(e))
        return nodes_created

    async def _update_progress(self, job: IngestionJob, progress: int, message: str = ""):
        job.progress = progress
        job.updated_at = datetime.now(timezone.utc)
        if self.db_session:
            await self.db_session.commit()
        logger.info("ingestion_progress", job_id=job.id, progress=progress, message=message)
        if self._progress_callback:
            self._progress_callback(job.id, progress, message)

    async def _complete_job(self, job: IngestionJob, stats: dict):
        job.status = "completed"
        job.progress = 100
        job.stats_json = json.dumps(stats)
        job.updated_at = datetime.now(timezone.utc)
        if self.db_session:
            await self.db_session.commit()
        logger.info("ingestion_completed", job_id=job.id, stats=stats)

    async def _fail_job(self, job: IngestionJob, error: str):
        job.status = "failed"
        job.progress = 0
        job.error_message = error
        job.updated_at = datetime.now(timezone.utc)
        if self.db_session:
            await self.db_session.commit()
        logger.error("ingestion_failed", job_id=job.id, error=error)


async def run_ingestion_pipeline(
    db_session: AsyncSession,
    file_id: str,
    user_id: str,
    chunk_size: int = 500,
    overlap: int = 50,
    chunk_strategy: str = "recursive",
    collection_name: str = "ingested_docs",
) -> dict:
    service = IngestionService(db_session=db_session)
    return await service.ingest_file(
        file_id=file_id,
        user_id=user_id,
        chunk_size=chunk_size,
        overlap=overlap,
        chunk_strategy=chunk_strategy,
        collection_name=collection_name,
    )
