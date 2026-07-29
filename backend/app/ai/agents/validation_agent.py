from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.logging import get_logger

logger = get_logger(__name__)


class ValidationAgent(BaseAgent):
    def __init__(self):
        super().__init__("validation_agent", "Response validator")

    async def process(self, message: Message) -> dict:
        response = message.payload.get("response", "")
        issues = []
        if len(response) < 10:
            issues.append("Response too short")
        return {"valid": len(issues) == 0, "issues": issues, "quality_score": 0.8 if len(issues) == 0 else 0.3}
