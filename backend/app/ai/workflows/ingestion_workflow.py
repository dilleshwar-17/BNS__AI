from app.logging import get_logger

logger = get_logger(__name__)


class IngestionWorkflow:
    async def execute(self, payload: dict) -> dict:
        source = payload.get("source", "")
        logger.info("ingestion_workflow_started", source=str(source)[:50])
        return {"source": source, "status": "ingested", "chunks": 0}
