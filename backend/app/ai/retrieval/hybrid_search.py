"""Hybrid retrieval pipeline with persistent clients and cached embeddings.

Singleton Chroma HTTP client (mirrors app.ingestion.chroma.vector_store),
a shared Ollama embedding path with an md5-keyed in-memory cache, and an
RRF fusion across vector / graph / keyword / section results. Searches the
bnsai_qa / bnsai_rag collections plus the user-scoped ingested_docs
collection so uploaded documents appear in chat context.
"""
import asyncio
import hashlib
import threading
import time

from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

_chroma_client = None
_lock = threading.Lock()
_last_health_check = 0.0
_HEALTH_CHECK_INTERVAL = 30.0

_embedding_cache: dict[str, list[float]] = {}
_EMBEDDING_CACHE_LIMIT = 4096

_neo4j_driver = None
_neo4j_last_fail: float | None = None
_NEO4J_COOLDOWN = 60.0

_COLLECTIONS = ("bnsai_qa", "bnsai_rag", "ingested_docs")
_EMBEDDING_MODEL = "nomic-embed-text"


def _md5_embedding(text: str) -> list[float]:
    digest = hashlib.md5(text.encode("utf-8")).digest()
    vec = [b / 255.0 for b in digest]
    return (vec * 6)[:64]


def _get_chroma_client():
    global _chroma_client, _last_health_check
    needs_reconnect = False

    with _lock:
        if _chroma_client is None:
            needs_reconnect = True
        elif time.time() - _last_health_check > _HEALTH_CHECK_INTERVAL:
            _last_health_check = time.time()
            try:
                _chroma_client.heartbeat()
            except Exception:
                needs_reconnect = True
                _chroma_client = None

        if needs_reconnect:
            import chromadb

            _chroma_client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                headers={"Authorization": f"Bearer {settings.chroma_token}"},
            )
            logger.info("retrieval_chroma_connected", host=settings.chroma_host, port=settings.chroma_port)

    return _chroma_client


async def _run_sync(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


def _get_collection(name: str):
    client = _get_chroma_client()
    try:
        return client.get_collection(name)
    except Exception:
        return None


async def _get_embedding(text: str) -> list[float]:
    key = text.strip()
    if key in _embedding_cache:
        return _embedding_cache[key]

    embedding = _md5_embedding(text)
    try:
        from app.integrations.ollama import get_ollama_client

        client = get_ollama_client()
        try:
            resp = await client.post(
                "/api/embeddings",
                json={"model": _EMBEDDING_MODEL, "prompt": text},
            )
            resp.raise_for_status()
            embedding = resp.json()["embedding"]
        except Exception:
            resp = await client.post(
                "/api/embed",
                json={"model": _EMBEDDING_MODEL, "input": [text]},
            )
            resp.raise_for_status()
            embedding = resp.json()["embeddings"][0]
    except Exception as e:
        logger.warning("embedding_failed_using_md5", error=str(e))

    if len(_embedding_cache) < _EMBEDDING_CACHE_LIMIT:
        _embedding_cache[key] = embedding
    return embedding


class RetrievalPipeline:
    def __init__(self):
        self.qa_collection = None
        self.text_collection = None
        self.user_collection = None

    async def _load_collections(self):
        def load():
            return {
                "qa": _get_collection("bnsai_qa"),
                "text": _get_collection("bnsai_rag"),
                "user": _get_collection("ingested_docs"),
            }

        cols = await _run_sync(load)
        self.qa_collection = cols["qa"]
        self.text_collection = cols["text"]
        self.user_collection = cols["user"]

    async def _query_collection(self, collection, query_emb: list[float], n_results: int, user_id: str | None = None):
        if collection is None:
            return []

        def query():
            if user_id:
                return collection.query(query_embeddings=[query_emb], n_results=n_results, where={"user_id": user_id})
            return collection.query(query_embeddings=[query_emb], n_results=n_results)

        try:
            res = await _run_sync(query)
        except Exception as e:
            logger.warning("vector_search_failed", error=str(e))
            return []

        if not res or not res.get("ids") or not res["ids"][0]:
            return []

        results = []
        for i in range(len(res["ids"][0])):
            results.append(
                {
                    "id": res["ids"][0][i],
                    "score": float(res["distances"][0][i]) if res.get("distances") else 0.0,
                    "text": res["documents"][0][i] if res.get("documents") else "",
                    "metadata": res["metadatas"][0][i] if res.get("metadatas") else {},
                    "source": "vector",
                }
            )
        return results

    async def search_vector(self, query: str, n_results: int = 10, user_id: str | None = None) -> list[dict]:
        query_emb = await _get_embedding(query)
        colls = [
            ("qa", self.qa_collection),
            ("text", self.text_collection),
        ]
        gathered = await asyncio.gather(
            *(self._query_collection(col, query_emb, n_results, None) for _, col in colls)
        )
        results = [item for sub in gathered for item in sub]

        if self.user_collection:
            user_results = await self._query_collection(self.user_collection, query_emb, n_results, user_id)
            results.extend(user_results)

        return results

    async def search_sections(self, sections: list[int]) -> list[dict]:
        if not sections:
            return []
        results = []
        if self.qa_collection:
            def get_by_sections():
                return self.qa_collection.get(where={"sections": {"$contains": str(sections[0])}})

            try:
                res = await _run_sync(get_by_sections)
                if res and res["ids"]:
                    for i in range(len(res["ids"])):
                        results.append(
                            {
                                "id": res["ids"][i],
                                "text": res["documents"][i] if res.get("documents") else "",
                                "metadata": res["metadatas"][i] if res.get("metadatas") else {},
                                "source": "section",
                            }
                        )
            except Exception as e:
                logger.warning("section_search_failed", error=str(e))
        return results

    async def _get_neo4j_driver(self):
        global _neo4j_driver, _neo4j_last_fail

        if _neo4j_driver is not None:
            return _neo4j_driver
        if _neo4j_last_fail and time.time() - _neo4j_last_fail < _NEO4J_COOLDOWN:
            return None

        try:
            from neo4j import AsyncGraphDatabase

            _neo4j_driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            return _neo4j_driver
        except Exception as e:
            _neo4j_last_fail = time.time()
            logger.warning("neo4j_driver_creation_failed", error=str(e))
            return None

    async def search_graph(self, query: str, classified_type: str = "") -> list[dict]:
        driver = await self._get_neo4j_driver()
        if driver is None:
            return []

        results = []
        try:
            async with driver.session(database="neo4j") as session:
                cypher = """
                    MATCH (q:Query)
                    WHERE toLower(q.text) CONTAINS toLower($query)
                    OPTIONAL MATCH (q)-[:REFERENCES_SECTION]->(s:Section)
                    OPTIONAL MATCH (q)-[:TAGGED_WITH]->(k:Keyword)
                    RETURN q.id AS id, q.text AS query, q.type AS type,
                           collect(DISTINCT s.number) AS sections,
                           collect(DISTINCT k.word) AS keywords
                    LIMIT 5
                """
                result = await session.run(cypher, query=query)
                records = await result.fetch(5)
                for record in records:
                    results.append(
                        {
                            "id": record.get("id"),
                            "text": f"Q: {record.get('query', '')}",
                            "metadata": {
                                "type": record.get("type"),
                                "sections": record.get("sections", []),
                                "keywords": record.get("keywords", []),
                                "source": "knowledge_graph",
                            },
                            "source": "graph",
                        }
                    )

                if classified_type:
                    type_cypher = """
                        MATCH (q:Query {type: $type})
                        OPTIONAL MATCH (q)-[:REFERENCES_SECTION]->(s:Section)
                        OPTIONAL MATCH (q)-[:TAGGED_WITH]->(k:Keyword)
                        RETURN q.id AS id, q.text AS query, q.type AS type,
                               collect(DISTINCT s.number) AS sections,
                               collect(DISTINCT k.word) AS keywords
                        LIMIT 5
                    """
                    type_result = await session.run(type_cypher, type=classified_type)
                    for record in await type_result.fetch(5):
                        if record.get("id") not in {r["id"] for r in results}:
                            results.append(
                                {
                                    "id": record.get("id"),
                                    "text": f"Q: {record.get('query', '')}",
                                    "metadata": {
                                        "type": record.get("type"),
                                        "sections": record.get("sections", []),
                                        "keywords": record.get("keywords", []),
                                        "source": "knowledge_graph",
                                    },
                                    "source": "graph",
                                }
                            )
        except Exception as e:
            global _neo4j_last_fail
            _neo4j_last_fail = time.time()
            logger.warning("graph_search_failed", error=str(e))

        return results

    async def search_keywords(self, query: str) -> list[dict]:
        if self.qa_collection is None:
            return []

        keywords = [w.lower() for w in query.split() if len(w) > 3]
        if not keywords:
            return []

        results = []

        def kw_search(kw: str):
            return self.qa_collection.get(where_document={"$contains": kw})

        for kw in keywords:
            try:
                res = await _run_sync(kw_search, kw)
                if res and res["ids"]:
                    for i in range(len(res["ids"])):
                        results.append(
                            {
                                "id": res["ids"][i],
                                "text": res["documents"][i] if res.get("documents") else "",
                                "metadata": res["metadatas"][i] if res.get("metadatas") else {},
                                "source": "keyword",
                            }
                        )
            except Exception as e:
                logger.warning("keyword_search_failed", error=str(e))

        seen = set()
        deduped = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                deduped.append(r)
        return deduped[:15]

    @staticmethod
    def _rrf_score(rank: int, k: int = 60) -> float:
        return 1.0 / (k + rank + 1)

    def _fusion_rank(
        self, vector_results: list, graph_results: list, keyword_results: list, section_results: list, top_k: int = 10
    ) -> list[dict]:
        grouped = [
            ("vector", vector_results, 1.0),
            ("graph", graph_results, 0.9),
            ("keyword", keyword_results, 0.5),
            ("section", section_results, 0.8),
        ]

        seen: dict[str, dict] = {}
        for list_label, results, weight in grouped:
            for rank, r in enumerate(results):
                rid = r.get("id")
                if not rid:
                    rid = f"{list_label}:{hash(r.get('text', '')) % 10**10}"
                if rid not in seen:
                    seen[rid] = {"result": {**r}, "score": 0.0, "sources": []}
                seen[rid]["score"] += weight * self._rrf_score(rank)
                seen[rid]["sources"].append(r.get("source", list_label))

        fused = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        out = []
        for item in fused[:top_k]:
            result = item["result"]
            result["sources"] = list(dict.fromkeys(item["sources"]))
            out.append(result)
        return out

    def _build_context(self, results: list[dict], max_tokens: int = 3000) -> str:
        parts = []
        char_budget = max_tokens * 4

        for r in results:
            text = r.get("text", "")
            if not text:
                continue
            meta = r.get("metadata", {}) or {}
            source_tag = r.get("source", "unknown")

            tags = [source_tag]
            if meta.get("query_type"):
                tags.append(str(meta["query_type"]))
            if meta.get("difficulty"):
                tags.append(str(meta["difficulty"]))
            if meta.get("source_file"):
                tags.append(str(meta["source_file"]))
            prefix = f"[{'|'.join(tags)}]"

            entry = f"{prefix} {text[:500]}"
            if len("\n".join(parts)) + len(entry) > char_budget:
                break
            parts.append(entry)

        return "\n\n".join(parts)

    async def retrieve(self, query: str, query_info: dict | None = None, top_k: int = 10, user_id: str | None = None) -> dict:
        await self._load_collections()

        classified_type = (query_info or {}).get("type", "")
        sections = (query_info or {}).get("sections", [])

        vector_results, graph_results, keyword_results, section_results = await asyncio.gather(
            self.search_vector(query, n_results=top_k * 2, user_id=user_id),
            self.search_graph(query, classified_type),
            self.search_keywords(query),
            self.search_sections(sections),
        )

        fused = self._fusion_rank(vector_results, graph_results, keyword_results, section_results, top_k=top_k)
        context = self._build_context(fused)

        return {
            "query": query,
            "classified_type": classified_type,
            "total_results": len(fused),
            "results": fused,
            "context": context,
            "breakdown": {
                "vector": len(vector_results),
                "graph": len(graph_results),
                "keyword": len(keyword_results),
                "section": len(section_results),
            },
        }
