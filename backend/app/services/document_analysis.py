"""Document analysis service (Phase 17).

Runs an evidence-grounded analysis over an uploaded user document:
    1. Extract text from the stored user file (pdf/docx/txt).
    2. Segment into issues using deterministic legal-offence pattern detection.
    3. For each issue, retrieve BNS evidence via the hybrid retriever.
    4. Assemble a grounded report binding each issue to its cited (verified)
       sections, enforcing strict user-doc vs legal-source separation.

Fail-closed: if the user document is empty/unreadable, analysis fails with no
content. The report only cites sections confirmed present in the retrieval
index; it never fabricates provisions.
"""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ingestion.extractor import extract_text
from app.models.analysis import (
    ANALYSIS_COMPLETED,
    ANALYSIS_FAILED,
    ANALYSIS_RUNNING,
    DocumentAnalysis,
)
from app.models.sources import SourceDocument
from app.retrieval.service import RetrievalService

# Legal-offence cue words used to segment a user document into candidate issues.
_ISSUE_PATTERN = re.compile(
    r"(theft|robbery|dacoity|assault|hurt|grievous hurt|cheating|fraud|"
    r"criminal breach of trust|defamation|criminal intimidation|forgery|"
    r"grabbing|extortion|rape|murder|kidnapping|abetment|public nuisance)",
    re.I,
)


class DocumentAnalysisService:
    """High-level analysis over a user document."""

    def __init__(self, retrieval: RetrievalService | None = None) -> None:
        settings = get_settings()
        self._retriever = retrieval or RetrievalService()
        self._max_issues = settings.analysis_max_issues

    async def analyze(self, session: AsyncSession, *, analysis: DocumentAnalysis) -> DocumentAnalysis:
        doc = analysis.document_text or ""
        analysis.status = ANALYSIS_RUNNING
        await session.flush()

        text = doc.strip()
        if not text:
            analysis.status = ANALYSIS_FAILED
            analysis.note = "empty_document"
            await session.flush()
            return analysis

        issues = self._detect_issues(text)
        if not issues:
            analysis.status = ANALYSIS_FAILED
            analysis.note = "no_legal_issues_detected"
            await session.flush()
            return analysis

        # Retrieve verified BNS evidence for each issue (no fabrication).
        mapped: list[dict] = []
        for issue in issues:
            refs = self._retrieve(issue)
            mapped.append({"issue": issue, "references": refs})
            if len(mapped) >= self._max_issues:
                break

        analysis.issues = mapped
        analysis.report = self._build_report(mapped)
        analysis.grounded = any(m["references"] for m in mapped)
        analysis.status = ANALYSIS_COMPLETED
        await session.flush()
        return analysis

    # -- helpers ------------------------------------------------------------

    @staticmethod
    async def read_document_text(document: SourceDocument) -> str:
        """Extract text from the stored file (user doc, never treated as legal source)."""
        path = Path(document.stored_path)
        if not path.exists():
            return ""
        try:
            return extract_text(path)
        except Exception:  # noqa: BLE001 - extraction failure for a user doc is not fatal
            return ""

    def _detect_issues(self, text: str) -> list[str]:
        matches: list[str] = []
        for m in re.finditer(_ISSUE_PATTERN, text):
            issue = m.group(1)
            if issue not in matches:
                matches.append(issue)
        return matches[: self._max_issues]

    def _retrieve(self, issue: str) -> list[dict]:
        try:
            outcome = self._retriever.retrieve(issue, fail_closed=False)
        except Exception:  # noqa: BLE001
            return []
        return [
            {
                "section_id": r.metadata.get("section_id"),
                "section_title": r.metadata.get("section_title"),
                "element_type": r.metadata.get("element_type"),
                "text": r.text,
                "score": round(r.score, 4),
            }
            for r in outcome.results
        ]

    def _build_report(self, mapped: list[dict]) -> str:
        lines = ["Document Legal Analysis\n"]
        for item in mapped:
            lines.append(f"- {item['issue']}:")
            if not item["references"]:
                lines.append("    (no verified BNS reference)")
                continue
            for ref in item["references"]:
                lines.append(f"    S.{ref['section_id']} — {ref['section_title'] or ''}")
        return "\n".join(lines)
