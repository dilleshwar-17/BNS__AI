from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.ai.orchestrator.pipeline import AIOrchestrator
from app.ai.workflows.research_workflow import ResearchWorkflow
from app.api.deps import get_current_user
from app.database.models.user import User
from app.schemas.research import ResearchRequest, ResearchResponse

router = APIRouter(prefix="/research", tags=["research"])
orchestrator = AIOrchestrator()
workflow = ResearchWorkflow()


@router.post("/", response_model=ResearchResponse)
async def research(body: ResearchRequest, user: User = Depends(get_current_user)):
    result = await workflow.execute(
        {"topic": body.topic, "depth": body.depth, "include_citations": body.include_citations}
    )
    findings = result.get("findings", [])
    return ResearchResponse(
        topic=body.topic,
        summary=result.get("summary", ""),
        findings=findings,
        citations=result.get("citations", []),
        generated_at=datetime.now(timezone.utc),
    )


@router.post("/deep", response_model=ResearchResponse)
async def deep_research(body: ResearchRequest, user: User = Depends(get_current_user)):
    result = await orchestrator.process(
        query=f"Conduct deep legal research on: {body.topic}",
        mode="deep_research",
        user_id=user.id,
    )
    return ResearchResponse(
        topic=body.topic,
        summary=result.get("response", ""),
        findings=result.get("sources", []),
        citations=[s.get("title", "") for s in result.get("sources", []) if s.get("title")],
        generated_at=datetime.now(timezone.utc),
    )
