from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.logging import get_logger

logger = get_logger(__name__)


class QueryRewriter(BaseAgent):
    def __init__(self):
        super().__init__("query_rewriter", "Query expansion and rewriting")

    async def process(self, message: Message) -> dict:
        query = message.payload.get("query", "")
        expanded = query
        if len(query.split()) < 3:
            expanded = f"Indian law: {query}"
        return {"original": query, "expanded": expanded, "rewritten": True}
