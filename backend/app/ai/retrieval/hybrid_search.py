from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class RetrievalPipeline:
    def __init__(self):
        self.chroma_client = None
        self.neo4j_driver = None
        self.qa_collection = None
        self.text_collection = None

    async def _init_clients(self):
        import chromadb

        self.chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            headers={"Authorization": f"Bearer {settings.chroma_token}"},
        )
        try:
            self.qa_collection = self.chroma_client.get_collection("bnsai_qa")
        except Exception:
            self.qa_collection = None
        try:
            self.text_collection = self.chroma_client.get_collection("bnsai_rag")
        except Exception:
            self.text_collection = None

        try:
            from neo4j import AsyncGraphDatabase

            self.neo4j_driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
        except Exception:
            self.neo4j_driver = None

    async def _get_embedding(self, text: str) -> list[float]:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                settings.ollama_base_url + "/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]

    async def search_vector(self, query: str, n_results: int = 10) -> list[dict]:
        results = []
        if self.qa_collection is None and self.text_collection is None:
            return results

        query_emb = await self._get_embedding(query)

        collections_to_search = []
        if self.qa_collection:
            collections_to_search.append(("qa", self.qa_collection))
        if self.text_collection:
            collections_to_search.append(("text", self.text_collection))

        for source, col in collections_to_search:
            try:
                res = col.query(query_embeddings=[query_emb], n_results=n_results)
                if res and res["ids"] and res["ids"][0]:
                    for i in range(len(res["ids"][0])):
                        results.append(
                            {
                                "id": res["ids"][0][i],
                                "score": res["distances"][0][i] if res.get("distances") else 0,
                                "text": res["documents"][0][i] if res.get("documents") else "",
                                "metadata": res["metadatas"][0][i] if res.get("metadatas") else {},
                                "source": source,
                            }
                        )
            except Exception as e:
                logger.warning("vector_search_failed", source=source, error=str(e))

        results.sort(key=lambda x: x["score"])
        return results

    async def search_sections(self, sections: list[int]) -> list[dict]:
        if not sections:
            return []
        results = []
        if self.qa_collection:
            try:
                for sec in sections:
                    res = self.qa_collection.get(
                        where={"sections": {"$contains": str(sec)}},
                    )
                    if res and res["ids"]:
                        for i in range(len(res["ids"])):
                            results.append(
                                {
                                    "id": res["ids"][i],
                                    "text": res["documents"][i] if res.get("documents") else "",
                                    "metadata": res["metadatas"][i] if res.get("metadatas") else {},
                                    "source": "section_filter",
                                    "section": sec,
                                }
                            )
            except Exception as e:
                logger.warning("section_search_failed", error=str(e))
        return results

    async def search_graph(self, query: str, classified_type: str = "") -> list[dict]:
        results = []
        if not self.neo4j_driver:
            return results

        try:
            async with self.neo4j_driver.session(database="neo4j") as session:
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
                            "source": "knowledge_graph",
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
                    type_records = await type_result.fetch(5)
                    for record in type_records:
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
                                    "source": "knowledge_graph",
                                }
                            )
        except Exception as e:
            logger.warning("graph_search_failed", error=str(e))

        return results

    async def search_keywords(self, query: str) -> list[dict]:
        results = []
        if self.qa_collection is None:
            return results

        keywords = [w.lower() for w in query.split() if len(w) > 3]
        if not keywords:
            return results

        try:
            for kw in keywords:
                res = self.qa_collection.get(
                    where_document={"$contains": kw},
                )
                if res and res["ids"]:
                    for i in range(len(res["ids"])):
                        results.append(
                            {
                                "id": res["ids"][i],
                                "text": res["documents"][i] if res.get("documents") else "",
                                "metadata": res["metadatas"][i] if res.get("metadatas") else {},
                                "source": "keyword",
                                "keyword": kw,
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

    def _fusion_rank(
        self, vector_results: list, graph_results: list, keyword_results: list, section_results: list, top_k: int = 10
    ) -> list[dict]:
        seen = {}
        rank = 0

        for r in vector_results:
            rid = r["id"]
            if rid not in seen:
                seen[rid] = {"result": r, "score": 0, "sources": []}
            seen[rid]["score"] += 1.0 / (rank + 1) if len(vector_results) > 0 else 0
            seen[rid]["sources"].append(r.get("source", "vector"))
            rank += 1

        rank = 0
        for r in graph_results:
            rid = r["id"]
            if rid not in seen:
                seen[rid] = {"result": r, "score": 0, "sources": []}
            seen[rid]["score"] += 1.0 / (rank + 1) if len(graph_results) > 0 else 0
            seen[rid]["sources"].append("graph")
            rank += 1

        rank = 0
        for r in keyword_results:
            rid = r["id"]
            if rid not in seen:
                seen[rid] = {"result": r, "score": 0, "sources": []}
            seen[rid]["score"] += 0.5 / (rank + 1) if len(keyword_results) > 0 else 0
            seen[rid]["sources"].append("keyword")
            rank += 1

        rank = 0
        for r in section_results:
            rid = r["id"]
            if rid not in seen:
                seen[rid] = {"result": r, "score": 0, "sources": []}
            seen[rid]["score"] += 0.8 / (rank + 1) if len(section_results) > 0 else 0
            seen[rid]["sources"].append("section")
            rank += 1

        fusion = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        return [item["result"] for item in fusion[:top_k]]

    def _build_context(self, results: list[dict], max_tokens: int = 3000) -> str:
        parts = []
        char_budget = max_tokens * 4

        for r in results:
            text = r.get("text", "")
            meta = r.get("metadata", {})
            if not text:
                continue

            source_tag = r.get("source", "unknown")
            prefix = f"[{source_tag}"
            if meta.get("query_type"):
                prefix += f":{meta['query_type']}"
            if meta.get("difficulty"):
                prefix += f":{meta['difficulty']}"
            prefix += "]"

            entry = f"{prefix} {text[:500]}"
            if len("\n".join(parts)) + len(entry) > char_budget:
                break
            parts.append(entry)

        return "\n\n".join(parts)

    async def retrieve(self, query: str, query_info: dict | None = None, top_k: int = 10) -> dict:
        await self._init_clients()

        classified_type = (query_info or {}).get("type", "")
        sections = (query_info or {}).get("sections", [])

        vector_results = await self.search_vector(query, n_results=top_k * 2)
        graph_results = await self.search_graph(query, classified_type)
        keyword_results = await self.search_keywords(query)
        section_results = await self.search_sections(sections)

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
