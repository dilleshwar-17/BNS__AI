from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.logging import get_logger
from app.services.drafting_service import DRAFT_TEMPLATES

logger = get_logger(__name__)


class DraftingAgent(BaseAgent):
    def __init__(self):
        super().__init__("drafting_agent", "Legal document drafting specialist")

    async def process(self, message: Message) -> dict:
        draft_type = message.payload.get("draft_type", "")
        details = message.payload.get("details", {})
        template = DRAFT_TEMPLATES.get(draft_type)
        if not template:
            return {"error": f"Unknown draft type: {draft_type}"}
        return {"draft_type": draft_type, "template": template["template"], "title": template["title"]}
