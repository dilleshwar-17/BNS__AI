from app.logging import get_logger

logger = get_logger(__name__)


class ResponseWorkflow:
    async def execute(self, payload: dict) -> dict:
        content = payload.get("content", "")
        logger.info("response_workflow_started", length=len(str(content)))
        return {"content": content, "formatted": True}
