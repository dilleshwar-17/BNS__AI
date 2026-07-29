from pydantic import BaseModel


class SearchQuery(BaseModel):
    query: str
    top_k: int = 5
    filters: dict | None = None


class SearchResult(BaseModel):
    id: str
    text: str
    score: float
    source: str
    metadata: dict | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str
