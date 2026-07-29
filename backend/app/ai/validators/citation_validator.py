import re
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

VALID_CITATION_PATTERNS = [
    re.compile(r"Section\s+\d+\s+(?:of\s+)?(?:the\s+)?(?:BNS|BNSS|BSA)", re.IGNORECASE),
    re.compile(r"\d{4}\s+(?:SCC|AIR|Cri LJ|Cri LJ)", re.IGNORECASE),
    re.compile(r"(?:20\d{2}|19\d{2})\s+\d+\s+SCC\s+\d+", re.IGNORECASE),
]

KNOWN_CASE_CITATIONS = [
    ("2024", "1", "SCC", "1"),
    ("2023", "9", "SCC", "1"),
    ("2020", "6", "SCC", "1"),
]


def validate_citations(text: str, context: Optional[str] = None) -> dict:
    found = []
    for pattern in VALID_CITATION_PATTERNS:
        found.extend(pattern.findall(text))

    invalid = _check_invalid_citations(text)
    format_issues = _check_formatting(found)

    overall_score = 1.0
    if invalid:
        overall_score -= len(invalid) * 0.2
    if format_issues:
        overall_score -= len(format_issues) * 0.1
    overall_score = max(0, overall_score)

    return {
        "score": overall_score,
        "passed": overall_score >= 0.6,
        "citations_found": len(found),
        "invalid_citations": invalid,
        "format_issues": format_issues,
        "suggestion": _suggest_improvements(invalid, format_issues),
    }


def _check_invalid_citations(text: str) -> list[str]:
    section_pattern = r"Section\s+(\d+)\s+(?:of\s+)?(?:the\s+)?(BNS|BNSS|BSA)"
    matches = re.findall(section_pattern, text, re.IGNORECASE)

    invalid = []
    for num_str, law in matches:
        num = int(num_str)
        max_sections = {"BNS": 399, "BNSS": 499, "BSA": 199}
        law_upper = law.upper()
        if law_upper in max_sections and num > max_sections[law_upper]:
            invalid.append(f"{law_upper} Section {num} exceeds known range")

    year_pattern = r"(\d{4})\s+\d+\s+SCC\s+\d+"
    year_matches = re.findall(year_pattern, text)
    for year_str in year_matches:
        year = int(year_str)
        if year > 2026 or year < 1950:
            invalid.append(f"Year {year} is outside reasonable range")

    return invalid


def _check_formatting(citations: list[str]) -> list[str]:
    issues = []
    for cite in citations:
        if re.match(r"\d{4}\s+\d+\s+SCC\s+\d+", cite):
            if not re.match(
                r"\d{4}\s+\d+\s+SCC\s+\d+\s*\((?:SC|Bom|Mad|Cal|Del|Ker|P&H|All|Pat|Raj|Gau|Or|Sikk|HPC|J&K)\)", cite
            ):
                issues.append(f"Citation missing court: {cite}")
    return issues


def _suggest_improvements(invalid: list[str], format_issues: list[str]) -> str:
    suggestions = []
    if invalid:
        suggestions.append("Verify section numbers against the latest BNS/BNSS/BSA text")
    if format_issues:
        suggestions.append("Add court abbreviation to SCC citations (e.g., '2024 SCC 1 (SC)')")
    return "; ".join(suggestions) if suggestions else "Citations appear valid"


def extract_citations(text: str) -> list[dict]:
    citations = []
    section_pattern = r"(?:Section|Sec\.?|S\.)\s*(\d+)\s+(?:of\s+)?(?:the\s+)?(BNS|BNSS|BSA)"
    for match in re.finditer(section_pattern, text, re.IGNORECASE):
        citations.append(
            {
                "type": "statute",
                "law": match.group(2).upper(),
                "section": int(match.group(1)),
                "text": match.group(0),
            }
        )

    case_pattern = r"(\d{4})\s+(\d+)\s+(SCC|AIR|Cri LJ)\s+(\d+)"
    for match in re.finditer(case_pattern, text):
        citations.append(
            {
                "type": "case",
                "year": int(match.group(1)),
                "volume": int(match.group(2)),
                "reporter": match.group(3),
                "page": int(match.group(4)),
                "text": match.group(0),
            }
        )

    return citations
