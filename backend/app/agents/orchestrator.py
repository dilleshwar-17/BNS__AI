"""Agentic orchestrator (Phase 8).

Runs the full chat workflow from docs/workflows.md:
    1. validate query (length, injection)
    2. classify intent / BNS scope
    3. retrieve relevant BNS evidence (fail-closed)
    4. build grounded context
    5. generate via LLM provider
    6. validate grounding / citations (reject unverifiable section cites)
    7. return structured outcome

Every step is bounded by ``max_agent_steps`` / ``agent_timeout_seconds`` config.
The LLM is never the source of truth: if retrieval yields insufficient evidence
or generation cites an unverified section, the orchestrator fails closed.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.agents.classifier import classify_intent, has_injection
from app.core.config import get_settings
from app.core.constants import INTENT_AMBIGUOUS, INTENT_OUT_OF_SCOPE
from app.core.exceptions import (
    AmbiguousQueryError,
    InsufficientBNSEvidenceError,
    LLMProviderUnavailableError,
    OutOfBNSScopeError,
    PromptInjectionDetectedError,
)
from app.llm.prompts import build_context, build_system_prompt, build_user_prompt
from app.llm.provider import LLMMessage, LLMProvider, get_llm_provider
from app.retrieval.service import RetrievalService
from app.validation.grounding import GroundingValidator


@dataclass
class EvidenceItem:
    chunk_id: uuid.UUID
    section_id: str | None
    section_title: str | None
    element_type: str | None
    text: str
    score: float

    def to_dict(self) -> dict:
        return {
            "chunk_id": str(self.chunk_id),
            "section_id": self.section_id,
            "section_title": self.section_title,
            "element_type": self.element_type,
            "text": self.text,
            "score": round(self.score, 4),
        }


@dataclass
class AgentOutcome:
    answer: str
    intent: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    grounded: bool = False
    model: str = ""
    note: str | None = None

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "intent": self.intent,
            "grounded": self.grounded,
            "model": self.model,
            "note": self.note,
            "evidence": [e.to_dict() for e in self.evidence],
        }


class AgentOrchestrator:
    """Coordinates validation -> retrieval -> generation -> grounding."""

    def __init__(
        self,
        *,
        retrieval: Optional[RetrievalService] = None,
        llm: Optional[LLMProvider] = None,
        grounding: Optional[GroundingValidator] = None,
    ) -> None:
        settings = get_settings()
        self._retrieval = retrieval or RetrievalService()
        self._llm = llm or get_llm_provider()
        self._grounding = grounding or GroundingValidator()
        self._max_steps = settings.max_agent_steps
        self._max_rounds = settings.max_retrieval_rounds

    def run(self, query: str) -> AgentOutcome:
        """Execute the agentic pipeline, failing closed on any gap."""
        q = (query or "").strip()

        # 1. Security: reject prompt injection before anything else.
        if has_injection(q):
            raise PromptInjectionDetectedError()

        # 2. Intent classification / scope guard.
        intent = classify_intent(q)
        if intent.intent == INTENT_AMBIGUOUS:
            raise AmbiguousQueryError()
        if intent.intent == INTENT_OUT_OF_SCOPE:
            raise OutOfBNSScopeError()

        # 3. Retrieval (fail-closed gate lives inside RetrievalService).
        try:
            outcome = self._retrieval.retrieve(q, fail_closed=True)
        except InsufficientBNSEvidenceError:
            raise

        evidence = [
            EvidenceItem(
                chunk_id=r.chunk_id,
                section_id=r.metadata.get("section_id"),
                section_title=r.metadata.get("section_title"),
                element_type=r.metadata.get("element_type"),
                text=r.text,
                score=r.score,
            )
            for r in outcome.results
        ]
        if not evidence:
            raise InsufficientBNSEvidenceError()

        context = build_context([e.to_dict() for e in evidence])

        # 4. Generation via the configured LLM provider.
        try:
            response = self._llm.generate(
                [
                    LLMMessage(role="system", content=build_system_prompt()),
                    LLMMessage(role="user", content=build_user_prompt(q, context, intent=intent.intent)),
                ],
                max_tokens=1024,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderUnavailableError() from exc
        answer = (response.text or "").strip()
        if not answer:
            raise LLMProviderUnavailableError(details={"reason": "empty generation"})

        # 5. Grounding validation (fail closed on unverified citations).
        allowed = [int(e.section_id) for e in evidence if e.section_id and e.section_id.isdigit()]
        grounding = self._grounding.validate(answer, allowed)

        return AgentOutcome(
            answer=answer,
            intent=intent.intent,
            evidence=evidence,
            grounded=grounding.grounded,
            model=response.model,
            note=grounding.message if not grounding.grounded else None,
        )
