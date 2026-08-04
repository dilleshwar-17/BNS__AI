"""Draft generation service (Phase 8)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.agents.orchestrator import AgentOrchestrator, EvidenceItem
from app.core.exceptions import DraftIncompleteError
from app.drafting.engine import validate_answers
from app.llm.prompts import build_context, build_system_prompt
from app.llm.provider import LLMMessage, LLMProvider, get_llm_provider


@dataclass
class DraftResult:
    content: str
    draft_type: str
    evidence: list[EvidenceItem]
    grounded: bool


class DraftingService:
    """Generates a grounded legal draft from questionnaire answers (fail-closed)."""

    def __init__(
        self,
        *,
        llm: Optional[LLMProvider] = None,
        orchestrator: Optional[AgentOrchestrator] = None,
    ) -> None:
        self._llm = llm or get_llm_provider()
        self._orchestrator = orchestrator or AgentOrchestrator()

    def generate(self, draft_type: str, answers: dict) -> DraftResult:
        errors = validate_answers(draft_type, answers)
        if errors:
            raise DraftIncompleteError(details={"errors": errors})

        # Use the orchestrator to retrieve BNS grounding for the narrative.
        narrative = (answers.get("facts") or "").strip()
        outcome = self._orchestrator.run(narrative) if narrative else None
        evidence = outcome.evidence if outcome else []

        context = build_context([e.to_dict() for e in evidence]) or "No statutory evidence retrieved."

        prompt = (
            f"Generate a {draft_type.replace('_', ' ')} for the client using "
            f"ONLY the BNS evidence below. Fill every provided questionnaire "
            f"field. Do not invent statutory provisions or section numbers.\n\n"
            f"Questionnaire answers:\n{self._fmt_answers(answers)}\n\n"
            f"=== BNS EVIDENCE ===\n{context}"
        )
        response = self._llm.generate(
            [
                LLMMessage(role="system", content=build_system_prompt()),
                LLMMessage(role="user", content=prompt),
            ],
            max_tokens=1800,
        )
        content = self._assemble(response.text, answers, draft_type)
        return DraftResult(
            draft_type=draft_type,
            evidence=evidence,
            grounded=True if outcome and outcome.grounded else False,
            content=content,
        )

    def _assemble(self, body: str, answers: dict, draft_type: str) -> str:
        header = f"{draft_type.replace('_', ' ').upper()}"
        lines = [header, "=" * len(header), ""]
        for key, value in answers.items():
            if (value or "").strip():
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        lines.extend(["", str(body or "").strip()])
        return "\n".join(lines)

    @staticmethod
    def _fmt_answers(answers: dict) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in answers.items() if (v or "").strip())
