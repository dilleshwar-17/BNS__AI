"""Legal-aware chunker: turns parsed elements into full-text chunks + sub-chunks.

A ``PARENT`` chunk holds the whole section (title + body + all sub-elements).
Each Explanation / Proviso / Illustration / Exception becomes a child chunk with
``parent_chunk_id`` pointing at the section, retaining the full ancestor chain in
metadata. Every chunk carries structural metadata and a content hash for
bag-of-n-grams style lexical indexing and dedup.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.ingestion.structure import ParsedElement

MIN_PARENT_CHARS = 80


@dataclass
class ChunkRecord:
    """A chunk ready for persistence/indexing."""

    text: str
    element_type: str
    section_num: str | None
    section_title: str | None
    chapter: str | None
    chapter_title: str | None
    marker: str | None
    position: int
    parent_text: str | None
    content_hash: str
    page_anchor: str | None = None

    @property
    def is_parent(self) -> bool:
        return self.element_type == "SECTION"


@dataclass
class ParentAssembly:
    section_text: str
    chapter: str | None
    chapter_title: str | None
    section_num: str | None
    section_title: str | None
    position: int


def chunk_document(elements: list[ParsedElement]) -> list[ChunkRecord]:
    """Group parsed elements into (parent, children) chunk records.

    A section plus its sub-elements becomes one parent chunk; each sub-element
    becomes a child chunk carrying the same section context plus a parent link.
    Long bodies are further split by token budget in ``finalize_chunks``.
    """
    records: list[ChunkRecord] = []
    # Collect per-section elements in order to assemble a parent body.
    section_elements: dict[str, list[ParsedElement]] = {}
    order: list[str] = []

    def group_key(el: ParsedElement) -> str:
        return el.section_num or f"s{el.position}"

    for el in elements:
        key = group_key(el)
        if key not in section_elements:
            section_elements[key] = []
        section_elements[key].append(el)
        if el.element_type == "SECTION":
            order.append(key)

    for sec_num in order:
        group = section_elements[sec_num]
        header = group[0] if group else None
        chapter = header.chapter if header else None
        chapter_title = header.chapter_title if header else None
        sec_title = header.section_title if header else None

        # Assemble parent text from header + body lines.
        parent_text = _assemble_text(group)

        parent = ChunkRecord(
            text=parent_text,
            element_type="SECTION",
            section_num=sec_num,
            section_title=sec_title,
            chapter=chapter,
            chapter_title=chapter_title,
            marker=sec_num,
            position=header.position if header else 0,
            parent_text=None,
            content_hash=_content_hash(parent_text),
        )
        records.append(parent)

        for sub in group:
            if sub.element_type == "SECTION":
                continue
            child = ChunkRecord(
                text=sub.text,
                element_type=sub.element_type,
                section_num=sec_num,
                section_title=sec_title,
                chapter=chapter,
                chapter_title=chapter_title,
                marker=sub.marker,
                position=sub.position,
                parent_text=parent_text,
                content_hash=_content_hash(sub.text),
            )
            records.append(child)

    return records


def _assemble_text(group: list[ParsedElement]) -> str:
    """Reconstruct a section's full text (header + body rows) for the parent chunk."""
    parts: list[str] = []
    header = group[0]
    if header.text:
        parts.append(header.text)
    for sub in group[1:]:
        if sub.text:
            parts.append(sub.text)
    return "\n\n".join(parts)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
