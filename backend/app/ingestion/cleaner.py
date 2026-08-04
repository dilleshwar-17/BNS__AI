"""Cleaning and normalization of extracted legal text (Phase 4)."""

from __future__ import annotations

import re

# Page headers/footers and artifacts common in legal PDFs.
_ARTIFACT_LINES = re.compile(r"^[\s\uf0b7•\-\uFFFD._*()]*\s*$")
_REPEATED_PAGE_NUMBER = re.compile(r"^\s*\d+\s*$")
_CHAPTER_HEADER = re.compile(r"^CHAPTER\s+([A-Z]+)\s*$", re.IGNORECASE)


def clean_text(raw: str) -> str:
    """Normalise extracted text: fix spacing, collapse blank runs, drop artifacts.

    Keeps all legal structure intact (chapters, numbered sections, keywords).
    """
    # Normalize line endings.
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    # Unbreak words split across soft line wraps in PDFs (e.g. "convec-\ntion").
    raw = re.sub(r"-\n(?=\w)", "", raw)

    lines = raw.split("\n")
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Drop empty/artifact-only lines but preserve structural breaks.
        if not stripped:
            cleaned.append("")
            continue
        if _ARTIFACT_LINES.match(stripped):
            # Keep chapter header lines; drop diagonal/ornament lines.
            if _CHAPTER_HEADER.match(stripped):
                cleaned.append(stripped)
                continue
            continue
        if _REPEATED_PAGE_NUMBER.match(stripped):
            continue
        cleaned.append(stripped)

    # Join with single newlines, preserving paragraph structure.
    text = "\n".join(cleaned)
    # Collapse 2+ blank lines into one.
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Normalize whitespace within lines (multiple spaces -> single).
    text = "\n".join(re.sub(r"[ \t]+", " ", ln) for ln in text.split("\n"))
    return text.strip()


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def remove_repeated_pagenumbers(lines: list[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        if _REPEATED_PAGE_NUMBER.match(ln):
            continue
        out.append(ln)
    return out
