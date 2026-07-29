import re

from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.logging import get_logger

logger = get_logger(__name__)


class CitationAgent(BaseAgent):
    def __init__(self):
        super().__init__("citation_agent", "Legal citation extractor and validator")
        self.citation_pattern = re.compile(
            r"(?i)(\d{4})\s+SCC\s+(Online\s+)?\w+\s+\d+|AIR\s+\d{4}\s+\w+\s+\d+|[\w\s]+v\.\s+[\w\s]+,\s+\d{4}"
        )

    async def process(self, message: Message) -> dict:
        text = message.payload.get("text", "")
        citations = self.citation_pattern.findall(text)
        return {"citations": citations, "count": len(citations)}
