from app.logging import get_logger

logger = get_logger(__name__)


class DraftingWorkflow:
    async def execute(self, payload: dict) -> dict:
        draft_type = payload.get("draft_type", "")
        details = payload.get("details", {})
        logger.info("drafting_workflow_started", draft_type=draft_type)
        return {"draft_type": draft_type, "details": details, "status": "drafting"}
