"""Legal structure detection (Act → Chapter → Section → Subsections → elements).

Parses cleaned text into a sequence of structural nodes used by the chunker.
This is deliberately deterministic and pattern-based (no LLM) so that accuracy
is auditable and reproducible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

CHAPTER_RE = re.compile(r"^CHAPTER\s*([A-Z]+)$", re.IGNORECASE)
SECTION_HEAD_RE = re.compile(r"^(?P<num>[0-9]+)\.\s+(?P<title>.*)$")
# "Explanation 2." / "Illustration (a)" / "Proviso." / "Exception 1." forms.
ELEMENT_HEAD_RE = re.compile(
    r"^(?P<kind>Explanation|Proviso|Illustration|Exception)\s*"
    r"(?P<marker>\([a-z0-9]+\)|[0-9]+)?[\.\u2014]?\s*(?P<title>.*)$"
)


@dataclass
class Element:
    kind: str  # CHAPTER | SECTION | EXPLANATION | PROVISO | ILLUSTRATION | EXCEPTION | BODY
    text: list[str]
    marker: str | None = None
    title: str = ""

    @property
    def full_text(self) -> str:
        return "\n".join(self.text)


@dataclass
class ParsedElement:
    element_type: str
    text: str
    chapter: str | None
    chapter_title: str | None
    section_num: str | None
    section_title: str | None
    marker: str | None
    position: int


def detect_structure(text: str) -> list[ParsedElement]:
    elements = _scan(text)
    return _finalize(elements)


def _scan(text: str) -> list[Element]:
    elements: list[Element] = []
    current: Element | None = None

    def flush() -> None:
        nonlocal current
        if current is not None and current.text:
            elements.append(current)
        current = None

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            flush()
            continue

        ch = CHAPTER_RE.match(line)
        sc = SECTION_HEAD_RE.match(line)
        el = ELEMENT_HEAD_RE.match(line)

        if ch:
            flush()
            current = Element(kind="CHAPTER", text=[line], marker=ch.group(1))
        elif sc:
            flush()
            current = Element(
                kind="SECTION",
                text=[line],
                marker=sc.group("num"),
                title=sc.group("title").strip(),
            )
        elif el:
            flush()
            current = Element(
                kind=el.group("kind").upper(),
                marker=(el.group("marker") or "") or None,
                title=el.group("title").strip(),
                text=[line],
            )
        else:
            if current is None:
                current = Element(kind="BODY", text=[line])
            else:
                current.text.append(line)

    flush()
    return elements


def _chapter_title(el: Element) -> str | None:
    for line in el.text[1:]:
        if line.strip():
            return line.strip()
    return el.marker


def _finalize(elements: list[Element]) -> list[ParsedElement]:
    current_chapter: str | None = None
    current_chapter_title: str | None = None
    current_sec_num: str | None = None
    current_sec_title: str | None = None
    out: list[ParsedElement] = []
    position = 0

    for el in elements:
        if el.kind == "CHAPTER":
            current_chapter = el.marker
            # Title is the first non-marker line following the CHAPTER header.
            current_chapter_title = _chapter_title(el)
            continue
        if el.kind == "SECTION":
            current_sec_num = el.marker
            current_sec_title = el.title or "Section"
            out.append(
                ParsedElement(
                    element_type="SECTION",
                    text=el.full_text,
                    chapter=current_chapter,
                    chapter_title=current_chapter_title,
                    section_num=current_sec_num,
                    section_title=current_sec_title,
                    marker=el.marker,
                    position=position,
                )
            )
            position += 1
            continue
        if current_sec_num is None:
            continue
        out.append(
            ParsedElement(
                element_type=el.kind,
                text=el.full_text,
                chapter=current_chapter,
                chapter_title=current_chapter_title,
                section_num=current_sec_num,
                section_title=current_sec_title,
                marker=el.marker,
                position=position,
            )
        )
        position += 1

    return out
