"""Query classification: intent + BNS scope + injection checks (Phase 8).

Deterministic, dependency-free classification (no LLM) so routing is robust and
explainable. Used by the orchestrator before retrieval/generation.
"""

from __future__ import annotations

import re

from app.core.constants import (
    INTENT_AMBIGUOUS,
    INTENT_DEFINITION,
    INTENT_FACT_SCENARIO,
    INTENT_FOLLOW_UP,
    INTENT_GENERAL_BNS_QUERY,
    INTENT_OUT_OF_SCOPE,
    INTENT_PUNISHMENT_LOOKUP,
    INTENT_RELATED_PROVISIONS,
    INTENT_SECTION_LOOKUP,
)

_PUNISHMENT_WORDS = ("punish", "penal", "sentence", "imprisonment", "fine", "penalty", "jail")
_DEFINITION_WORDS = ("define", "definition", "what is meant", "is defined as")
_SCENARIO_HINT = re.compile(
    r"\b(if a person|if someone|scenario|suppose|in the following case|would it be|is it an offence)\b",
    re.IGNORECASE,
)
_SECTION_HINT = re.compile(r"\bsection\s+(\d{1,3})\b|\bs/(\d{1,3})\b", re.IGNORECASE)
_OFFENCE_HINT = re.compile(r"offence|offense|criminal", re.IGNORECASE)
_EXCEPTION_HINT = re.compile(r"exception|exception to|but not where", re.IGNORECASE)
_RELATED_HINT = re.compile(
    r"related provisions|same chapter|also provide|what else" r"|other sections|connected sections", re.IGNORECASE
)
_FOLLOWUP_WORDS = ("what about", "how does that", "additionally", "and also", "can you also")
_OUT_OF_SCOPE_CLUE = (
    "cpc",
    "crpc",
    "ipc",
    "contract act",
    "income tax",
    "gst",
    "motor vehicles",
    "divorce act",
    "specific relief",
)
_FOLLOWUP_CLUE = ("what about", "how does that", "additionally", "and also")
_AMBIGUOUS_CLUE = ("?", "about", "etc")

# Prompt-injection / attempts to escape the retrieval boundary.
INJECTION_PATTERNS = (
    re.compile(r"ignore (all )?(previous|above|prior) (instructions|prompts)", re.I),
    re.compile(r"\bsystem prompt\b", re.I),
    re.compile(r"\bdo not follow\b", re.I),
    re.compile(r"\bdisregard\b", re.I),
    re.compile(r"you are now (unconstrained|ungrounded|free)", re.I),
)


class IntentResult:
    """Structured classification result."""

    def __init__(self, intent: str, *, query: str, confidence: float = 1.0) -> None:
        self.intent = intent
        self.query = query
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {"intent": self.intent, "confidence": self.confidence}


def has_injection(query: str) -> bool:
    return any(pattern.search(query) for pattern in INJECTION_PATTERNS)


def classify_intent(query: str) -> IntentResult:
    """Return the best-guess intent for a free-text query."""
    q = (query or "").strip()
    ql = q.lower()

    if has_injection(q):
        return IntentResult(INTENT_AMBIGUOUS, query=q)

    if _SECTION_HINT.search(q) and ("punish" in ql or "punishment" in ql or "penalty" in ql):
        return IntentResult(INTENT_PUNISHMENT_LOOKUP, query=q)

    if any(w in ql for w in _DEFINITION_WORDS):
        return IntentResult(INTENT_DEFINITION, query=q)

    if _EXCEPTION_HINT.search(q):
        return IntentResult(INTENT_FACT_SCENARIO, query=q)

    if any(w in ql for w in _PUNISHMENT_WORDS):
        return IntentResult(INTENT_PUNISHMENT_LOOKUP, query=q)

    if _SECTION_HINT.search(q):
        return IntentResult(INTENT_SECTION_LOOKUP, query=q)

    if any(clue in ql for clue in _OUT_OF_SCOPE_CLUE):
        return IntentResult(INTENT_OUT_OF_SCOPE, query=q)

    if any(w in ql for w in _FOLLOWUP_WORDS):
        return IntentResult(INTENT_FOLLOW_UP, query=q)

    if _RELATED_HINT.search(q):
        return IntentResult(INTENT_RELATED_PROVISIONS, query=q)

    return IntentResult(INTENT_GENERAL_BNS_QUERY, query=q)
