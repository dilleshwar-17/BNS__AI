from datetime import datetime

from pydantic import BaseModel


class DraftGenerate(BaseModel):
    draft_type: str
    details: dict | None = None


class SaveRawDraft(BaseModel):
    draft_type: str
    title: str
    content: str


class DraftResponse(BaseModel):
    id: str
    user_id: str
    title: str
    content: str
    doc_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DraftTemplate(BaseModel):
    title: str
    template: str


class FieldDefinition(BaseModel):
    id: str
    label: str
    type: str
    required: bool = False
    placeholder: str | None = None
    help_text: str | None = None
    default: str | int | float | bool | None = None
    validation: dict | None = None
    options: list[dict] | None = None


class QuestionGroup(BaseModel):
    id: str
    title: str
    description: str
    fields: list[FieldDefinition]


class QuestionnaireResponse(BaseModel):
    draft_type: str
    title: str
    description: str
    groups: list[QuestionGroup]


class ValidationError(BaseModel):
    field: str
    message: str


class ValidationRequest(BaseModel):
    draft_type: str
    group_id: str | None = None
    details: dict


class ValidationResponse(BaseModel):
    valid: bool
    errors: list[ValidationError]


class SuggestRequest(BaseModel):
    draft_type: str
    field_id: str
    context: dict | None = None


class SuggestResponse(BaseModel):
    suggestion: str
    confidence: float = 0.0


class SessionResponse(BaseModel):
    id: str
    draft_type: str
    current_step: int
    total_steps: int
    progress: float
    form_data: dict | None = None
    status: str
    updated_at: str


class SaveProgressRequest(BaseModel):
    draft_type: str
    current_step: int = 0
    form_data: dict = {}


class StartDraftRequest(BaseModel):
    template: str | None = None
    draft_type: str | None = None


class StartDraftResponse(BaseModel):
    session_id: str
    draft_type: str
    title: str
    questionnaire: QuestionnaireResponse


class AnswerRequest(BaseModel):
    field_key: str | None = None
    field_value: str | int | float | bool | list | dict | None = None
    answers: dict | None = None


class AnswerResponse(BaseModel):
    session_id: str
    field_key: str | None = None
    saved: bool = True
    updated_at: str
