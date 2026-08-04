"""Extract cross-section references from legal chunk text.

Phase 7: builds a knowledge graph over BNS sections. This module finds the
explicit cross-references that a section makes to other sections (e.g. "subject
to the restrictions contained in section 37", "as defined in clause (31) of
section 3"), which become typed ``REFERENCES`` edges in the graph.
"""

from __future__ import annotations

import re

MIN_SECTION = 1
MAX_SECTION = 358

# A "section" reference, optionally a list: "section 37", "sections 25, 26 and
# 27", "of section 8". We capture the whole matched text then pull numbers out.
_SECTION_RE = re.compile(
    r"\bsection\b\s+([0-9]{1,3}(?:\s*,\s*[0-9]{1,3})*(?:\s+and\s+[0-9]{1,3})?)",
    re.IGNORECASE,
)
_SECTION_LIST_RE = re.compile(
    r"\bsections\b\s+([0-9]{1,3}(?:\s*,\s*[0-9]{1,3})*(?:\s+and\s+[0-9]{1,3})?)",
    re.IGNORECASE,
)
# "sub-section(s) (N) of section M" -> reference to section M.
_SUB_OF_REF_RE = re.compile(r"\bsub-sections?\s*\([^)]*\)\s+of\s+section\s+([0-9]{1,3})", re.IGNORECASE)
_NUM_RE = re.compile(r"[0-9]{1,3}")


def extract_section_references(text: str) -> dict[str, set[int]]:
    """Return explicit + subsection section-number references.

    Only numbers in the authoritative BNS range (1..358) are kept; references to
    external Acts (e.g. "section 474 of the BNSS") are excluded automatically.
    """
    explicit: set[int] = set()

    for pattern in (_SECTION_RE, _SECTION_LIST_RE):
        for match in pattern.finditer(text):
            for num in map(int, _NUM_RE.findall(match.group(1))):
                if MIN_SECTION <= num <= MAX_SECTION:
                    explicit.add(num)

    subsection: set[int] = {num for num in map(int, _SUB_OF_REF_RE.findall(text)) if MIN_SECTION <= num <= MAX_SECTION}

    return {"explicit": explicit, "subsection": subsection}
