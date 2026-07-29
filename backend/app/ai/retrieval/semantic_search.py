from app.logging import get_logger

logger = get_logger(__name__)


class SemanticSearch:
    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        try:
            from app.ingestion.chroma.vector_store import query_vector_store

            result = await query_vector_store(query, top_k)
            if result:
                return [{"text": result, "score": 1.0, "source": "vector"}]
        except Exception as e:
            logger.warning("semantic_search_failed", error=str(e))
        return []
