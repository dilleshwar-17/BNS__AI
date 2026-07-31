from fastapi import APIRouter, Depends

from app.ai.retrieval.hybrid_search import RetrievalPipeline
from app.api.deps import get_current_user
from app.database.models.user import User
from app.schemas.retrieval import SearchQuery, SearchResponse, SearchResult

router = APIRouter(prefix="/retrieval", tags=["retrieval"])
pipeline = RetrievalPipeline()


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchQuery, user: User = Depends(get_current_user)):
    result = await pipeline.retrieve(body.query, top_k=body.top_k, user_id=user.id)
    results = [
        SearchResult(
            id=r.get("id", ""),
            text=r.get("text", ""),
            score=r.get("score", 0.0),
            source=r.get("source", "unknown"),
            metadata=r.get("metadata"),
        )
        for r in result.get("results", [])
    ]
    return SearchResponse(
        results=results,
        total=result.get("total_results", len(results)),
        query=body.query,
    )
