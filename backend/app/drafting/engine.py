"""Drafting engine (Phase 8) — from docs/drafting.md.

Template catalogue for supported legal documents, a questionnaire, and a
generator that assembles a grounded draft using retrieved BNS evidence. Drafts
are grounded on retrieved sections only (fail-closed), are not stored by
default, and can be exported as TXT.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DRAFT_TYPES = [
    "FIR",
    "LEGAL_NOTICE",
    "BAIL_APPLICATION",
    "AFFIDAVIT",
    "CONSUMER_COMPLAINT",
    "PERSONAL_BOND",
]


@dataclass
class DraftQuestion:
    key: str
    label: str
    required: bool = True
    options: list[str] = field(default_factory=list)


@dataclass
class DraftType:
    name: str
    title: str
    description: str
    questions: list[DraftQuestion] = field(default_factory=list)


QUESTIONNAIRES: dict[str, list[DraftQuestion]] = {
    "FIR": [
        DraftQuestion("complainant", "Complainant name"),
        DraftQuestion("accused", "Accused name (if known)"),
        DraftQuestion("date", "Date of occurrence"),
        DraftQuestion("place", "Place of occurrence"),
        DraftQuestion("facts", "Brief narrative of facts"),
    ],
    "LEGAL_NOTICE": [
        DraftQuestion("from_party", "Sender name"),
        DraftQuestion("to_party", "Recipient name"),
        DraftQuestion("nature", "Nature of the claim"),
        DraftQuestion("facts", "Brief narrative of facts"),
    ],
    "BAIL_APPLICATION": [
        DraftQuestion("court", "Court name"),
        DraftQuestion("accused", "Accused name"),
        DraftQuestion("case_no", "Case/CR number"),
        DraftQuestion("grounds", "Grounds for bail"),
        DraftQuestion("facts", "Brief narrative"),
    ],
}


def list_draft_types() -> list[dict]:
    return [
        {
            "name": name,
            "title": _draft_type(name).title,
            "description": _draft_type(name).description,
            "questions": [
                {
                    "key": q.key,
                    "label": q.label,
                    "required": q.required,
                    "options": q.options,
                }
                for q in _draft_type(name).questions
            ],
        }
        for name in DRAFT_TYPES
    ]


def _draft_type(name: str) -> DraftType:
    return DraftType(
        name=name,
        title=name.replace("_", " ").title(),
        description=f"Auto-generated {name.replace('_', ' ').title()} grounded in BNS provisions.",
        questions=QUESTIONNAIRES.get(name, []),
    )


def get_draft_type(name: str) -> DraftType:
    """Public accessor for a single draft type (raises ValueError if unknown)."""
    if name not in DRAFT_TYPES:
        raise ValueError(f"Unknown draft type: {name}")
    return _draft_type(name)


def validate_answers(draft_type_name: str, answers: dict) -> list[str]:
    """Return missing-required-field errors."""
    errors: list[str] = []
    questions = QUESTIONNAIRES.get(draft_type_name, [])
    for q in questions:
        if q.required and not (answers.get(q.key) or "").strip():
            errors.append(f"Missing required field: {q.label}")
    if draft_type_name not in DRAFT_TYPES:
        errors.append(f"Unsupported draft type: {draft_type_name}")
    return errors
