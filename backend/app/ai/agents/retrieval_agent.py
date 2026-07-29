import asyncio

from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.integrations.ollama import get_ollama_client

logger = get_logger(__name__)
settings = get_settings()


async def _run_sync(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


class RetrievalAgent(BaseAgent):
    def __init__(self):
        super().__init__("retrieval_agent", "Agentic RAG retrieval with strategy selection and fusion")
        self.subscribe_to("retrieve")
        self.chroma_client = None
        self.neo4j_driver = None

    async def _init_clients(self):
        import chromadb

        self.chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            headers={"Authorization": f"Bearer {settings.chroma_token}"},
        )
        from neo4j import AsyncGraphDatabase

        self.neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def process(self, message: Message) -> dict:
        query = message.payload.get("query", "")
        classification = message.payload.get("classification", {})
        user_id = message.payload.get("user_id")
        return await self.retrieve(query, classification, user_id)

    async def get_collections(self):
        def _get():
            try:
                return {
                    "qa": self.chroma_client.get_collection("bnsai_qa"),
                    "text": self.chroma_client.get_collection("bnsai_rag"),
                }
            except Exception:
                return {}

        return await _run_sync(_get)

    async def _get_embedding(self, text: str) -> list[float]:
        client = get_ollama_client()
        resp = await client.post(
            "/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
        )
        if resp.status_code == 404:
            logger.warning("ollama_embedding_model_missing", model="nomic-embed-text")
            raise RuntimeError("Ollama embedding model 'nomic-embed-text' not loaded")
        resp.raise_for_status()
        return resp.json()["embedding"]

    def _select_strategies(self, classification: dict) -> list[str]:
        strategies = ["vector"]
        ctype = classification.get("primary_type", "")
        complexity = classification.get("complexity", "medium")

        if classification.get("sections"):
            strategies.append("section")
        if ctype in ("comparison", "deep_research", "multi-hop"):
            strategies.append("graph")
            strategies.append("decompose")
        if complexity in ("medium", "hard"):
            strategies.append("keyword")
            strategies.append("expand")

        logger.info("strategies_selected", strategies=strategies, type=ctype)
        return strategies

    async def retrieve(self, query: str, classification: dict, user_id: str | None = None) -> dict:
        if not self.chroma_client:
            try:
                await self._init_clients()
            except Exception as e:
                return {"error": f"Failed to init clients: {e}", "results": [], "context": ""}

        strategies = self._select_strategies(classification)
        all_results = []
        sections = classification.get("sections", [])
        sections_list = sections if isinstance(sections, list) else []
        collections = await self.get_collections()

        if "vector" in strategies:
            vec_results = await self._vector_search(query, collections)
            all_results.extend(vec_results)

        if "section" in strategies and sections_list:
            sec_results = await self._section_search(sections_list, collections)
            all_results.extend(sec_results)

        if "keyword" in strategies:
            kw_results = await self._keyword_search(query, collections)
            all_results.extend(kw_results)

        if "graph" in strategies:
            try:
                graph_results = await self._graph_search(query, classification)
                all_results.extend(graph_results)
            except Exception as e:
                logger.warning("graph_search_failed", error=str(e))

        if "decompose" in strategies:
            sub_queries = self._decompose(query, classification)
            for sq in sub_queries[1:4]:
                sq_results = await self._vector_search(sq, collections)
                all_results.extend(sq_results[:3])

        fused = self._fusion_rank(all_results)
        context = self._build_context(fused)

        if user_id:
            profile = self.get_user_profile(user_id)
            profile.record_query(classification.get("primary_type", ""), "", sections_list)

        return {
            "query": query,
            "strategies_used": strategies,
            "total_raw": len(all_results),
            "total_fused": len(fused),
            "results": fused[:10],
            "context": context,
            "breakdown": {s: 1 for s in strategies},
        }

    def _query_collection_sync(self, col, query_texts, n_results):
        return col.query(query_texts=query_texts, n_results=n_results)

    def _get_collection_sync(self, col, where=None, where_document=None):
        if where:
            return col.get(where=where)
        if where_document:
            return col.get(where_document=where_document)
        return col.get()

    async def _vector_search(self, query: str, collections: dict) -> list[dict]:
        results = []
        for source, col in collections.items():
            try:
                res = await _run_sync(self._query_collection_sync, col, [query], 5)
                if res and res["ids"] and res["ids"][0]:
                    for i in range(len(res["ids"][0])):
                        results.append(
                            {
                                "id": res["ids"][0][i],
                                "score": res["distances"][0][i] if res.get("distances") else 1.0,
                                "text": res["documents"][0][i] if res.get("documents") else "",
                                "metadata": res["metadatas"][0][i] if res.get("metadatas") else {},
                                "source": f"vector_{source}",
                            }
                        )
            except Exception as e:
                logger.warning("vector_search_failed", source=source, error=str(e))
        return results

    async def _section_search(self, sections: list[int], collections: dict) -> list[dict]:
        results = []
        col = collections.get("qa")
        if not col:
            return results
        for sec in sections:
            try:
                res = await _run_sync(self._get_collection_sync, col, where={"sections": {"$contains": str(sec)}})
                if res and res["ids"]:
                    for i in range(len(res["ids"])):
                        results.append(
                            {
                                "id": res["ids"][i],
                                "text": res["documents"][i] if res.get("documents") else "",
                                "metadata": res["metadatas"][i] if res.get("metadatas") else {},
                                "source": "section",
                                "section": sec,
                            }
                        )
            except Exception:
                pass
        return results

    async def _keyword_search(self, query: str, collections: dict) -> list[dict]:
        results = []
        col = collections.get("qa")
        if not col:
            return results
        words = [w.lower() for w in query.split() if len(w) > 3][:5]
        for kw in words:
            try:
                res = await _run_sync(self._get_collection_sync, col, where_document={"$contains": kw})
                if res and res["ids"]:
                    for i in range(min(3, len(res["ids"]))):
                        results.append(
                            {
                                "id": res["ids"][i],
                                "text": res["documents"][i] if res.get("documents") else "",
                                "metadata": res["metadatas"][i] if res.get("metadatas") else {},
                                "source": "keyword",
                            }
                        )
            except Exception:
                pass
        return self._dedupe(results)

    async def _graph_search(self, query: str, classification: dict) -> list[dict]:
        if not self.neo4j_driver:
            return []
        results = []
        ctype = classification.get("primary_type", "")

        async with self.neo4j_driver.session(database="neo4j") as session:
            cypher = """
                MATCH (q:Query)
                WHERE toLower(q.text) CONTAINS toLower($q_text)
                RETURN q.id AS id, q.text AS text, q.type AS type, q.difficulty AS difficulty
                LIMIT 5
            """
            result = await session.run(cypher, {"q_text": query[:80]})
            records = await result.fetch(5)
            for record in records:
                results.append(
                    {
                        "id": record.get("id", ""),
                        "text": f"Related: {record.get('text', '')}",
                        "metadata": {"type": record.get("type"), "difficulty": record.get("difficulty")},
                        "source": "graph",
                    }
                )

            if ctype:
                type_cypher = """
                    MATCH (q:Query {type: $type})
                    RETURN q.id AS id, q.text AS text, q.type AS type
                    LIMIT 3
                """
                type_result = await session.run(type_cypher, type=ctype)
                type_records = await type_result.fetch(3)
                existing_ids = {r["id"] for r in results if r.get("id")}
                for record in type_records:
                    if record.get("id") not in existing_ids:
                        results.append(
                            {
                                "id": record.get("id", ""),
                                "text": f"[{ctype}] {record.get('text', '')}",
                                "metadata": {"type": ctype},
                                "source": "graph_type",
                            }
                        )
        return results

    def _decompose(self, query: str, classification: dict) -> list[str]:
        ctype = classification.get("primary_type", "")
        if ctype == "comparison":
            parts = query.rsplit(" vs ", 1)
            if len(parts) < 2:
                parts = query.rsplit(" vs. ", 1)
            return [query] + [f"Explain {p.strip()}" for p in parts[:2]]
        if ctype == "deep_research":
            return [query, f"Overview of {query[:60]}", f"Key provisions {query[:50]}"]
        if classification.get("sections"):
            sections = classification["sections"]
            return [query] + [f"Section {s} BNS" for s in sections[:3]]
        return [query]

    def _fusion_rank(self, results: list[dict], top_k: int = 10) -> list[dict]:
        seen = {}
        for rank, r in enumerate(results):
            rid = r.get("id", r.get("text", "")[:50])
            if rid not in seen:
                seen[rid] = {"result": r, "score": 0, "sources": set()}
            seen[rid]["score"] += 1.0 / (rank + 1)
            seen[rid]["sources"].add(r.get("source", "unknown"))

        fusion = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        for item in fusion:
            item["result"]["fusion_score"] = round(item["score"], 3)
            item["result"]["sources"] = list(item["sources"])
        return [item["result"] for item in fusion[:top_k]]

    def _build_context(self, results: list[dict], max_chars: int = 4000) -> str:
        parts = []
        chars = 0
        for r in results:
            text = r.get("text", "")
            if not text:
                continue
            tag = r.get("source", "unknown")
            entry = f"[{tag}] {text[:400]}"
            if chars + len(entry) > max_chars:
                break
            parts.append(entry)
            chars += len(entry)
        return "\n\n".join(parts)

    def _dedupe(self, items: list[dict]) -> list[dict]:
        seen = set()
        result = []
        for item in items:
            rid = item.get("id", item.get("text", "")[:30])
            if rid not in seen:
                seen.add(rid)
                result.append(item)
        return result


retrieval_agent = RetrievalAgent()
