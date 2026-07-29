from app.logging import get_logger

logger = get_logger(__name__)


class ChatWorkflow:
    async def execute(self, payload: dict) -> dict:
        query = payload.get("query", "")
        mode = payload.get("mode", "legal_guidance")
        logger.info("chat_workflow_started", query=query[:50], mode=mode)
        return {"query": query, "mode": mode, "status": "processing"}
