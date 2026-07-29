from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    user_id: str
    title: str
    content: str
    doc_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpload(BaseModel):
    title: str
    content: str
    doc_type: str = "upload"
