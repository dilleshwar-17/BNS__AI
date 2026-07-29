import re
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

BNS_SECTIONS = {
    "BNS": list(range(1, 400)),
    "BNSS": list(range(1, 500)),
    "BSA": list(range(1, 200)),
}


def check_hallucination(response: str, context: Optional[str] = None, query: Optional[str] = None) -> dict:
    checks = {
        "section_citation_valid": _check_section_citations(response),
        "no_false_statements": _check_false_statements(response, context),
        "temporal_consistency": _check_temporal_consistency(response),
        "jurisdiction_check": _check_jurisdiction(response),
    }

    overall_score = sum(1 for v in checks.values() if v["passed"]) / len(checks) if checks else 0.0

    return {
        "score": overall_score,
        "passed": overall_score >= 0.7,
        "checks": checks,
        "warning": _generate_warning(checks),
    }


def _check_section_citations(text: str) -> dict:
    section_pattern = r"(?:Section|Sec\.?|S\.)\s*(\d+)(?:\s*(?:of|under)\s*(?:the\s*)?(BNS|BNSS|BSA|Indian Penal Code|CrPC|Evidence Act))?"
    matches = re.findall(section_pattern, text, re.IGNORECASE)

    invalid = []
    for num_str, law in matches:
        num = int(num_str)
        law_upper = law.upper() if law else "BNS"
        if law_upper in ("INDIAN PENAL CODE", "CRPC", "EVIDENCE ACT"):
            law_upper = {"INDIAN PENAL CODE": "BNS", "CRPC": "BNSS", "EVIDENCE ACT": "BSA"}.get(law_upper, "BNS")

        if law_upper in BNS_SECTIONS:
            max_section = max(BNS_SECTIONS[law_upper])
            if num > max_section + 50:
                invalid.append(f"{law_upper} Section {num} (max ~{max_section})")

    return {
        "passed": len(invalid) == 0,
        "invalid_citations": invalid,
    }


def _check_false_statements(response: str, context: Optional[str] = None) -> dict:
    red_flags = [
        (r"guarante?es?\s+(?:acquittal|bail|win)", "Overpromising outcome"),
        (r"always\s+(?:results?\s+in|leads?\s+to)", "Absolute statement"),
        (r"definitely\s+(?:will|shall)", "Guarantee language"),
        (r"100%\s+(?:success|effective)", "Absolute claim"),
    ]

    issues = []
    for pattern, desc in red_flags:
        if re.search(pattern, response, re.IGNORECASE):
            issues.append(desc)

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def _check_temporal_consistency(text: str) -> dict:
    bns_mentioned = bool(re.search(r"\bBNS\b", text))
    ipc_mentioned = bool(re.search(r"\bIPC\b|Indian Penal Code", text, re.IGNORECASE))

    inconsistent = bns_mentioned and ipc_mentioned

    return {
        "passed": not inconsistent,
        "inconsistent": inconsistent,
        "message": "Mixes BNS and IPC references" if inconsistent else None,
    }


def _check_jurisdiction(text: str) -> dict:
    non_indian = re.search(r"\b(?:federal|US|UK|American)\s+court", text, re.IGNORECASE)
    return {
        "passed": not bool(non_indian),
        "non_indian_reference": bool(non_indian),
    }


def _generate_warning(checks: dict) -> Optional[str]:
    failed = [k for k, v in checks.items() if not v.get("passed")]
    if not failed:
        return None
    return f"Potential issues detected: {', '.join(failed)}. Please verify with a qualified legal professional."
