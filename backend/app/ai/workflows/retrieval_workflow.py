from app.logging import get_logger

logger = get_logger(__name__)


class RetrievalWorkflow:
    async def execute(self, payload: dict) -> dict:
        query = payload.get("query", "")
        strategy = payload.get("strategy", "hybrid")
        logger.info("retrieval_workflow_started", query=query[:50], strategy=strategy)
        return {"query": query, "strategy": strategy, "results": [], "context": ""}
