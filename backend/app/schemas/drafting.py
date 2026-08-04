"""Drafting API schemas (Phase 8)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DraftQuestionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    required: bool = True
    options: list[str] = []


class DraftTypeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    title: str
    description: str
    questions: list[DraftQuestionSchema] = []


class DraftTypesResponse(BaseModel):
    draft_types: list[DraftTypeSchema]


class DraftGenerateRequest(BaseModel):
    draft_type: str
    answers: dict = {}


class DraftGenerateResponse(BaseModel):
    draft_type: str
    content: str
    grounded: bool
    citations: list[str] = []
