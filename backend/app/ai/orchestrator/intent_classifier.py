import re


class IntentClassifier:
    def __init__(self):
        self.patterns = {
            "drafting": re.compile(
                r"(?i)\b(draft|prepare|create|generate|write)\s+(a|an|the)?\s*"
                r"(fir|legal notice|bail|affidavit|complaint|agreement|plaint|divorce|will|notice|deed|petition)\b"
            ),
            "section_lookup": re.compile(r"(?i)\b(section|article|clause|provision)\s+\d+"),
            "comparison": re.compile(r"(?i)\b(compare|difference|vs|versus|distinguish|differ|differentiate)\b"),
            "legal_procedure": re.compile(
                r"(?i)\b(procedure|process|steps?|how to file|how to apply|how to register|timeline|stages?)\b"
            ),
            "rights_advisory": re.compile(
                r"(?i)\b(my right|my rights|fundamental right|constitutional right|legal right|human right|entitled|"
                r"can they|can I|am I allowed|is it legal)\b"
            ),
            "case_law": re.compile(
                r"(?i)\b(case law|judgment|precedent|supreme court|high court|landmark|ratio|citation|overruled|upheld)\b"
            ),
            "deep_research": re.compile(
                r"(?i)\b(research|comprehensive|detailed analysis|in-depth|thorough|full analysis|elaborate)\b"
            ),
            "document_analysis": re.compile(
                r"(?i)\b(analyze|review|examine)\s+(this|the|my)?\s*(document|contract|agreement|notice|affidavit|deed)\b"
            ),
            "product_info": re.compile(
                r"(?i)\b(what is bns|about bns|what can you|features|capabilities|what do you do)\b"
            ),
            "greeting": re.compile(
                r"(?i)^(hi|hello|hey|greetings|good morning|good evening|good afternoon|namaste|namaskar)\b"
            ),
            "legal_guidance": re.compile(
                r"(?i)\b(what|how|explain|tell|guide|define|meaning|means|define|describe|clarify)\b.*"
                r"\b(law|legal|section|court|offence|offense|crime|criminal|punishment|penalty|fine|imprisonment|"
                r"arrest|bail|charge|trial|appeal|suit|plaint|claim|notice|right|act|code|sanhita)\b"
            ),
        }

    async def classify(self, query: str) -> dict:
        query_lower = query.lower().strip()

        best_intent = "legal_guidance"
        best_confidence = 0.0

        for intent, pattern in self.patterns.items():
            match = pattern.search(query_lower)
            if match:
                match_len = len(match.group())
                query_len = len(query_lower)
                confidence = min(0.95, 0.5 + (match_len / max(query_len, 1)) * 0.5)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_intent = intent

        complexity = "medium"
        if any(w in query_lower for w in ["explain in detail", "comprehensive", "elaborate", "in-depth", "thorough"]):
            complexity = "hard"
        elif any(w in query_lower for w in ["simple", "brief", "short", "quick"]):
            complexity = "easy"

        sections = re.findall(r"(?i)section\s+(\d+[a-zA-Z]*)", query_lower)

        return {
            "intent": best_intent,
            "confidence": round(best_confidence, 2),
            "complexity": complexity,
            "sections": sections,
        }
