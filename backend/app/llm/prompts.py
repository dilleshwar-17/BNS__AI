"""Prompt templates for agent generation (Phase 8).

System + Context + Conversation + Query, per docs/prompts.md. Prompts are
versioned here so changes are auditable and the LLM is kept strictly grounded
to the provided BNS evidence (never allowed to invent statutory content).
"""

from __future__ import annotations

from app.core.constants import (
    INTENT_FOLLOW_UP,
    INTENT_GENERAL_BNS_QUERY,
)

SYSTEM_GROUNDED = (
    "You are BNS AI, a legal assistant for the Bharatiya Nyaya Sanhita (BNS) 2023. "
    "Answer legal questions using ONLY the BNS evidence provided in the context. "
    "Do not invent sections, numbers, punishments, or legal rules. "
    "Never cite a section that is not present in the context. "
    "If the evidence is insufficient, say clearly that it is insufficient rather than guessing. "
    "Use plain, professional legal language."
)


def build_system_prompt() -> str:
    return SYSTEM_GROUNDED


def build_user_prompt(query: str, context: str, *, intent: str = INTENT_GENERAL_BNS_QUERY) -> str:
    if intent == INTENT_FOLLOW_UP:
        intro = "Consider the conversation context and answer the follow-up."
    else:
        intro = "Answer the user's legal question grounded strictly in the BNS evidence below."
    return f"{intro}\n\n=== BNS EVIDENCE ===\n{context}\n\n=== QUESTION ===\n{query}"


def build_context(evidence: list[dict], max_chars: int = 12000) -> str:
    """Serialize retrieved evidence into a compact context block for the LLM."""
    parts: list[str] = []
    budget = max_chars
    for item in evidence:
        text = (item.get("text") or "").strip()
        sec = item.get("section_id") or ""
        if not text:
            continue
        block = f"[{sec}] {text}"
        if len(block) > budget:
            remaining = budget
            block = f"[{sec}] {text[:remaining]}"
        if len(block) <= 0:
            continue
        parts.append(block)
        budget -= len(block)
        if budget <= 0:
            break
    return "\n\n".join(parts)
