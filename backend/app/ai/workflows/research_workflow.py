from app.ai.orchestrator.pipeline import AIOrchestrator
from app.core.logging import get_logger

logger = get_logger(__name__)

orchestrator = AIOrchestrator()


class ResearchWorkflow:
    async def execute(self, payload: dict) -> dict:
        topic = payload.get("topic", "")
        depth = payload.get("depth", "medium")
        include_citations = payload.get("include_citations", True)
        logger.info("research_workflow_started", topic=topic[:50], depth=depth)

        result = await orchestrator.process(
            query=f"Research topic: {topic}. Provide comprehensive legal analysis with section references.",
            mode="deep_research",
        )

        findings = []
        citations = []

        for src in result.get("sources", []):
            finding = {
                "title": src.get("title", ""),
                "content": src.get("text", ""),
                "relevance": src.get("score", 0),
                "source": src.get("source", "unknown"),
            }
            findings.append(finding)
            if include_citations and src.get("title"):
                citations.append(src.get("title", ""))

        summary = result.get("response", "")

        return {
            "topic": topic,
            "depth": depth,
            "findings": findings,
            "citations": citations,
            "summary": summary,
            "status": "completed",
        }
