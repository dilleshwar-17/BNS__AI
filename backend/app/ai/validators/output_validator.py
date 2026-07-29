import re

from app.core.logging import get_logger

logger = get_logger(__name__)

CLASSIFIER_PATTERNS = {
    "section_lookup": [
        r"section\s+\d+",
        r"s\.\s*\d+",
        r"what does section",
        r"explain section",
        r"tell me about section",
        r"section.*say",
    ],
    "comparison": [
        r"vs\.?",
        r"difference between",
        r"compare",
        r"distinguish",
        r"versus",
        r"different from",
        r"how.*different",
    ],
    "legal_procedure": [
        r"procedure",
        r"how to file",
        r"process",
        r"steps",
        r"how do I",
        r"how can I",
        r"apply for",
        r"file a",
        r"register a",
    ],
    "rights_advisory": [
        r"rights?",
        r"can they",
        r"what can I do",
        r"protected",
        r"entitled",
        r"fundamental right",
        r"violation of",
    ],
    "legal_drafting": [
        r"draft",
        r"write a",
        r"format of",
        r"template for",
        r"notice",
        r"petition",
        r"application for",
    ],
    "case_law": [
        r"case law",
        r"landmark",
        r"judgment",
        r"supreme court",
        r"precedent",
        r"ruling",
        r"held that",
    ],
    "deep_research": [
        r"comprehensive",
        r"detailed analysis",
        r"explain.*in detail",
        r"overview of",
        r"discuss",
        r"elaborate",
        r"all about",
        r"complete guide",
        r"everything about",
    ],
    "legal_guidance": [
        r"what is",
        r"what are",
        r"meaning of",
        r"define",
        r"definition",
        r"explain",
        r"tell me about",
    ],
}


def classify_query(query: str) -> str:
    query_lower = query.lower().strip()
    scores = {}

    for mode, patterns in CLASSIFIER_PATTERNS.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, query_lower)
            score += len(matches)
        if score > 0:
            scores[mode] = score

    if not scores:
        return "legal_guidance"

    return max(scores, key=scores.get)


def expand_query(query: str, classified_type: str) -> dict:
    query_lower = query.lower()
    expansions = {
        "original": query,
        "type": classified_type,
        "sections": [],
        "keywords": [],
        "sub_queries": [],
    }

    section_matches = re.findall(r"(?:section|s\.|sec\.)\s*(\d+)", query_lower, re.IGNORECASE)
    expansions["sections"] = [int(s) for s in section_matches]

    if classified_type == "comparison":
        parts = re.split(r"\s+vs\.?\s+", query)
        if len(parts) >= 2:
            expansions["sub_queries"] = [p.strip() for p in parts[:3]]

    if classified_type == "deep_research":
        expansions["sub_queries"] = [
            f"overview of {query_lower[:60]}",
            f"key provisions {query_lower[:60]}",
            f"punishment for {query_lower[:60]}",
        ]

    if classified_type == "multi-hop":
        sentences = re.split(r"[.!?]+", query)
        expansions["sub_queries"] = [s.strip() for s in sentences if len(s.strip()) > 10][:5]

    return expansions


def decompose_query(query: str, classified_type: str) -> list[str]:
    sub_queries = [query]

    if classified_type in ("deep_research", "long analysis"):
        sub_queries = [
            f"What is {query[:60]}?",
            f"What are the key sections for {query[:60]}?",
            f"What are the punishments under {query[:60]}?",
        ]

    if classified_type == "comparison":
        sub_queries = [
            f"Explain first concept: {query}",
            f"Explain second concept: {query}",
            f"Differences: {query}",
        ]

    section_nums = re.findall(r"section\s+(\d+)", query, re.IGNORECASE)
    if section_nums:
        for s in section_nums[:3]:
            sub_queries.append(f"Section {s} BNS")

    return sub_queries
