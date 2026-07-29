import asyncio
import json
from pathlib import Path

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.integrations.ollama import get_ollama_client

logger = get_logger(__name__)
settings = get_settings()

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "BNS_queries" / "BNS_QUERIES"
EMBED_MODEL = "nomic-embed-text"


async def _run_sync(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


class IngestionPipeline:
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.neo4j_driver = None
        self.total_ingested = 0

    def _init_chroma_sync(self):
        import chromadb

        self.chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            headers={"Authorization": f"Bearer {settings.chroma_token}"},
        )
        try:
            self.collection = self.chroma_client.get_collection("bnsai_rag")
        except Exception:
            self.collection = self.chroma_client.create_collection("bnsai_rag")

    async def _init_chroma(self):
        await _run_sync(self._init_chroma_sync)

    async def _init_neo4j(self):
        from neo4j import AsyncGraphDatabase

        self.neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def _get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        client = get_ollama_client()
        resp = await client.post(
            "/api/embed",
            json={"model": EMBED_MODEL, "input": texts},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]

    def _count_sync(self):
        return self.collection.count()

    def _add_sync(self, texts, embeddings, ids, metadatas):
        self.collection.add(documents=texts, embeddings=embeddings, ids=ids, metadatas=metadatas)

    async def ingest_full_text(self) -> int:
        full_path = DATA_DIR / "bns_full.txt"
        if not full_path.exists():
            logger.error("bns_full.txt not found")
            return 0

        text = full_path.read_text(encoding="utf-8")
        chunks = self._chunk_text(text)
        logger.info("full_text_chunked", chunks=len(chunks))

        await self._init_chroma()
        existing = await _run_sync(self._count_sync)
        if existing > 0:
            logger.info("chroma_already_populated", count=existing)
            return existing

        batch_size = 20
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c["text"] for c in batch]
            embeddings = await self._get_embeddings_batch(texts)
            ids = [c["id"] for c in batch]
            metadatas = [c["metadata"] for c in batch]
            await _run_sync(self._add_sync, texts, embeddings, ids, metadatas)
            self.total_ingested += len(batch)
            logger.info("ingested_batch", batch=i // batch_size + 1, count=len(batch), total=self.total_ingested)

        logger.info("full_text_ingestion_complete", chunks=len(chunks))
        return len(chunks)

    def _chunk_text(self, text: str) -> list[dict]:
        lines = text.split("\n")
        chunks = []
        current_chunk = []
        current_section = "Preamble"
        chunk_id = 0

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("CHAPTER "):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "id": f"bns_text_{chunk_id}",
                            "text": chunk_text,
                            "metadata": {
                                "source": "bns_full",
                                "type": "section",
                                "section": current_section,
                                "chunk": chunk_id,
                            },
                        }
                    )
                    chunk_id += 1
                    current_chunk = []
                current_section = stripped
            elif stripped.startswith("--- PAGE") and current_chunk:
                chunk_text = "\n".join(current_chunk)
                if len(chunk_text.strip()) > 50:
                    chunks.append(
                        {
                            "id": f"bns_text_{chunk_id}",
                            "text": chunk_text,
                            "metadata": {
                                "source": "bns_full",
                                "type": "section",
                                "section": current_section,
                                "chunk": chunk_id,
                            },
                        }
                    )
                    chunk_id += 1
                current_chunk = []
            else:
                if stripped:
                    current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "id": f"bns_text_{chunk_id}",
                    "text": chunk_text,
                    "metadata": {
                        "source": "bns_full",
                        "type": "section",
                        "section": current_section,
                        "chunk": chunk_id,
                    },
                }
            )

        return chunks

    async def ingest_rag_dataset(self) -> int:
        rag_path = DATA_DIR / "bns_rag_dataset.jsonl"
        if not rag_path.exists():
            logger.error("bns_rag_dataset.jsonl not found")
            return 0

        entries = []
        with rag_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        logger.info("rag_dataset_loaded", entries=len(entries))

        def _get_or_create_collection():
            try:
                return self.chroma_client.get_collection("bnsai_qa")
            except Exception:
                return self.chroma_client.create_collection("bnsai_qa")

        rag_collection = await _run_sync(_get_or_create_collection)

        def _count_collection():
            return rag_collection.count()

        existing = await _run_sync(_count_collection)
        if existing > 0:
            logger.info("qa_collection_already_populated", count=existing)
            return existing

        def _add_batch(texts, embeddings, ids, metadatas):
            rag_collection.add(documents=texts, embeddings=embeddings, ids=ids, metadatas=metadatas)

        batch_size = 20
        for i in range(0, len(entries), batch_size):
            batch = entries[i : i + batch_size]
            texts = []
            ids = []
            metadatas = []
            for e in batch:
                text = f"Q: {e['query']}\nA: {e['answer']}\nKeywords: {', '.join(e.get('keywords', []))}"
                texts.append(text)
                ids.append(f"qa_{e['id']}")
                metadatas.append(
                    {
                        "id": e["id"],
                        "query_type": e["query_type"],
                        "difficulty": e.get("difficulty", "medium"),
                        "chapter": e.get("chapter", ""),
                        "sections": str(e.get("section", [])),
                        "keywords": ", ".join(e.get("keywords", [])),
                    }
                )

            embeddings = await self._get_embeddings_batch(texts)
            await _run_sync(_add_batch, texts, embeddings, ids, metadatas)
            self.total_ingested += len(batch)

            if (i // batch_size) % 10 == 0:
                logger.info("qa_ingested", batch=i // batch_size + 1, total=len(entries))

        logger.info("rag_dataset_ingestion_complete", entries=len(entries))
        return len(entries)

    async def build_knowledge_graph(self) -> int:
        await self._init_neo4j()
        rag_path = DATA_DIR / "bns_rag_dataset.jsonl"
        entries = []
        with rag_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        async with self.neo4j_driver.session(database="neo4j") as session:
            result = await session.run("MATCH (n:Query) RETURN count(n) AS count")
            record = await result.single()
            if record and record["count"] > 0:
                logger.info("graph_already_populated", count=record["count"])
                return record["count"]

            for e in entries:
                params = {
                    "id": e["id"],
                    "q_text": e["query"],
                    "type": e["query_type"],
                    "difficulty": e.get("difficulty", "medium"),
                }
                await session.run(
                    """
                    MERGE (q:Query {id: $id})
                    SET q.text = $q_text, q.type = $type, q.difficulty = $difficulty
                    """,
                    params,
                )

                for sec in e.get("section", []):
                    await session.run(
                        """
                        MATCH (q:Query {id: $id})
                        MERGE (s:Section {number: $sec})
                        MERGE (q)-[:REFERENCES_SECTION]->(s)
                        """,
                        id=e["id"],
                        sec=sec,
                    )

                chapter = e.get("chapter", "")
                if chapter:
                    await session.run(
                        """
                        MATCH (q:Query {id: $id})
                        MERGE (c:Chapter {name: $chapter})
                        MERGE (q)-[:BELONGS_TO]->(c)
                        """,
                        id=e["id"],
                        chapter=chapter,
                    )

                keywords = e.get("keywords", [])
                for kw in keywords[:5]:
                    await session.run(
                        """
                        MATCH (q:Query {id: $id})
                        MERGE (k:Keyword {word: $kw})
                        MERGE (q)-[:TAGGED_WITH]->(k)
                        """,
                        id=e["id"],
                        kw=kw.lower(),
                    )

            count_result = await session.run("MATCH (n:Query) RETURN count(n) AS count")
            record = await count_result.single()
            count = record["count"] if record else 0
            logger.info("knowledge_graph_built", nodes=count)
            return count

    async def ingest_pdf_full_text(self) -> int:
        pdf_path = DATA_DIR / "bns_full_pdf.txt"
        if not pdf_path.exists():
            logger.info("pdf_text_not_found", path=str(pdf_path))
            return 0

        text = pdf_path.read_text(encoding="utf-8")
        chunks = self._chunk_text(text)
        logger.info("pdf_text_chunked", chunks=len(chunks))

        await self._init_chroma()
        existing = await _run_sync(self._count_sync)
        if existing > 0:
            logger.info("chroma_already_populated", count=existing)
            return existing

        batch_size = 20
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c["text"] for c in batch]
            embeddings = await self._get_embeddings_batch(texts)
            ids = [c["id"] for c in batch]
            metadatas = [c["metadata"] for c in batch]
            await _run_sync(self._add_sync, texts, embeddings, ids, metadatas)
            self.total_ingested += len(batch)
            logger.info("ingested_pdf_batch", batch=i // batch_size + 1, count=len(batch), total=self.total_ingested)

        logger.info("pdf_text_ingestion_complete", chunks=len(chunks))
        return len(chunks)

    async def run_all(self, use_pdf: bool = False) -> dict:
        logger.info("pipeline_ingestion_started")
        results = {"full_text": 0, "rag_qa": 0, "graph_nodes": 0, "pdf_text": 0}

        await self._init_chroma()
        pdf_path = DATA_DIR / "bns_full_pdf.txt"
        if use_pdf and pdf_path.exists():
            results["pdf_text"] = await self.ingest_pdf_full_text()
        results["full_text"] = await self.ingest_full_text()
        results["rag_qa"] = await self.ingest_rag_dataset()
        results["graph_nodes"] = await self.build_knowledge_graph()

        if self.neo4j_driver:
            await self.neo4j_driver.close()

        logger.info("pipeline_ingestion_complete", results=results)
        return results


async def run_ingestion(use_pdf: bool = False):
    pipeline = IngestionPipeline()
    return await pipeline.run_all(use_pdf=use_pdf)
