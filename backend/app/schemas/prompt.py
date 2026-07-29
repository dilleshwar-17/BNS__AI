from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PromptBase(BaseModel):
    name: str
    category: str
    content: str
    is_active: bool = True


class PromptCreate(PromptBase):
    pass


class PromptUpdate(BaseModel):
    category: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    changelog: Optional[str] = None


class PromptVersionResponse(BaseModel):
    id: str
    version: int
    content: str
    changelog: Optional[str] = None
    is_active: bool
    created_at: datetime
    created_by: Optional[str] = None

    model_config = {"from_attributes": True}


class PromptResponse(BaseModel):
    id: str
    name: str
    category: str
    current_version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    versions: List[PromptVersionResponse] = []

    model_config = {"from_attributes": True}


class PromptActivateVersion(BaseModel):
    version: int
