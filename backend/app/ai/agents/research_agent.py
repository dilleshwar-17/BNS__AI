from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.logging import get_logger

logger = get_logger(__name__)


class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("research_agent", "Legal research specialist")

    async def process(self, message: Message) -> dict:
        query = message.payload.get("query", "")
        return {"query": query, "status": "research_initiated", "findings": []}
