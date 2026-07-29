from datetime import datetime

from pydantic import BaseModel


class ResearchRequest(BaseModel):
    topic: str
    depth: str = "medium"
    include_citations: bool = True


class ResearchResponse(BaseModel):
    topic: str
    summary: str
    findings: list[dict]
    citations: list[str]
    generated_at: datetime
