import re

from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.core.logging import get_logger

logger = get_logger(__name__)


class ResponseVerifierAgent(BaseAgent):
    def __init__(self):
        super().__init__("response_verifier", "Validates response quality, citations, and hallucination risk")
        self.subscribe_to("verify_response")

    async def process(self, message: Message) -> dict:
        payload = message.payload
        return self.verify(
            query=payload.get("query", ""),
            response=payload.get("response", ""),
            context=payload.get("context", ""),
            classification=payload.get("classification", {}),
        )

    def verify(self, query: str, response: str, context: str = "", classification: dict | None = None) -> dict:
        issues = []
        score = 1.0
        signals = {}

        if len(response) < 20:
            issues.append("Response too short to be useful")
            score -= 0.4
            signals["too_short"] = True

        response_lower = response.lower()
        refusal_phrases = [
            "i don't know",
            "i cannot",
            "i'm not able",
            "i am not able",
            "i cannot provide",
            "i don't have",
            "unable to",
        ]
        for phrase in refusal_phrases:
            if phrase in response_lower:
                issues.append(f"Model refused: '{phrase}'")
                score -= 0.3
                signals["refusal"] = phrase
                break

        sections = classification.get("sections", []) if classification else []
        if sections:
            for s in sections:
                if str(s) not in response:
                    issues.append(f"Section {s} requested but not addressed in response")
                    score -= 0.05

        citation_patterns = [
            (r"\d{4}\s+SCC\s+\d+", "SCC citation"),
            (r"AIR\s+\d{4}\s+(SC|HC)", "AIR citation"),
            (r"MANU/", "Manupatra citation"),
            (r"SCC\s+Online\s+(SC|HC|Del|Bom|Mad|Kar|Cal)", "SCC Online"),
        ]
        found_citations = []
        for pattern, label in citation_patterns:
            matches = re.findall(pattern, response)
            if matches:
                found_citations.extend(matches)

        signals["citations_found"] = len(found_citations)

        section_refs = re.findall(r"Section\s+(\d+)", response, re.IGNORECASE)
        signals["sections_mentioned"] = [int(s) for s in section_refs]

        context_sections = set()
        if context:
            context_secs = re.findall(r"Section\s+(\d+)", context, re.IGNORECASE)
            context_sections = set(int(s) for s in context_secs if s.isdigit())

        if section_refs and context_sections:
            response_set = set(int(s) for s in section_refs if s.isdigit())
            overlap = response_set & context_sections
            if len(overlap) < len(response_set) * 0.3 and len(response_set) > 0:
                signals["hallucination_risk"] = "low_overlap_with_context"
                score -= 0.15

        if len(response) > 2000:
            signals["comprehensive"] = True
            score = min(score + 0.05, 1.0)

        self.log(
            "verified", score=score, issues=len(issues), citations=len(found_citations), sections=len(section_refs)
        )

        return {
            "verified": score >= 0.5,
            "quality_score": round(score, 3),
            "issues": issues,
            "signals": signals,
            "citations_found": found_citations,
            "sections_mentioned": signals.get("sections_mentioned", []),
            "response_length": len(response),
            "hallucination_risk": "low" if score >= 0.7 else ("medium" if score >= 0.4 else "high"),
        }


response_verifier = ResponseVerifierAgent()
