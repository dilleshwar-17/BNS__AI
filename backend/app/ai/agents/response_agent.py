from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.logging import get_logger

logger = get_logger(__name__)


class ResponseAgent(BaseAgent):
    def __init__(self):
        super().__init__("response_agent", "Final response formatter")

    async def process(self, message: Message) -> dict:
        content = message.payload.get("content", "")
        mode = message.payload.get("mode", "legal_guidance")
        return {"content": content, "mode": mode, "formatted": True}
