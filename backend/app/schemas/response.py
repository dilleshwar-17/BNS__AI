from datetime import datetime

from pydantic import BaseModel


class APIResponse(BaseModel):
    success: bool = True
    data: dict | None = None
    message: str | None = None
    error: str | None = None
    timestamp: datetime = datetime.now()
