from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.logging import get_logger

logger = get_logger(__name__)


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("planner_agent", "Query planning and decomposition")

    async def process(self, message: Message) -> dict:
        query = message.payload.get("query", "")
        steps = ["retrieve", "analyze", "generate", "validate"]
        return {"query": query, "plan": steps, "steps_count": len(steps)}
