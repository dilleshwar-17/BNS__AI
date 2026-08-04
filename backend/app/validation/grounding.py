"""Grounding validator (Phase 8).

Confirms the generated answer does not cite a section that was not present in
the retrieved evidence. This is the final fail-closed guarantee: the LLM may
only reference legal content that survived retrieval + the minimum-score gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from app.core.exceptions import GroundingValidationFailedError

_SECTION_CITE = re.compile(r"\bsections?\s+(\d{1,3}(?:\s*,\s*\d{1,3})*(?:\s+and\s+\d{1,3})?)\b", re.IGNORECASE)
_NUM = re.compile(r"\d{1,3}")


@dataclass
class GroundingResult:
    grounded: bool
    stray: list[int]
    message: str | None = None


class GroundingValidator:
    """Validate cited sections are backed by retrieved evidence."""

    def validate(self, answer: str, evidence_sections: Iterable[int]) -> GroundingResult:
        allowed = set(int(s) for s in evidence_sections if s is not None)
        cited = {int(n) for n in _NUM.findall(" ".join(_SECTION_CITE.findall(answer)))}
        stray = [n for n in sorted(cited) if n not in allowed]
        if stray:
            return GroundingResult(
                grounded=False,
                stray=stray,
                message=f"Citations to unverified sections: {stray}",
            )
        return GroundingResult(grounded=True, stray=[])


def assert_grounded(answer: str, evidence_sections: Sequence[int]) -> GroundingResult:
    """Validate and raise if ungrounded, returning the result on success."""
    result = GroundingValidator().validate(answer, evidence_sections)
    if not result.grounded:
        raise GroundingValidationFailedError(details={"stray_sections": result.stray, "message": result.message})
    return result
