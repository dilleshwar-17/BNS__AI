from datetime import datetime

from pydantic import BaseModel


class IngestionJobResponse(BaseModel):
    id: str
    filename: str
    doc_type: str
    status: str
    progress: int
    error_message: str | None = None
    chunks_count: int = 0
    stats: dict = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IngestionJobListResponse(BaseModel):
    total: int
    jobs: list[IngestionJobResponse]


class DocumentListItem(BaseModel):
    id: str
    filename: str
    file_size: int
    mime_type: str | None = None
    file_type: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentListItem]
