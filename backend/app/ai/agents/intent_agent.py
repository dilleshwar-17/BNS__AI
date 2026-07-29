import re

from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message

CLASSIFIER_PATTERNS = {
    "section_lookup": [r"section\s+\d+", r"s\.\s*\d+", r"what does section", r"explain section", r"section.*say"],
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
    "legal_drafting": [r"draft", r"write a", r"format of", r"template for", r"notice", r"petition", r"application for"],
    "case_law": [r"case law", r"landmark", r"judgment", r"supreme court", r"precedent", r"ruling", r"held that"],
    "deep_research": [
        r"comprehensive",
        r"detailed analysis",
        r"explain.*in detail",
        r"overview of",
        r"discuss",
        r"elaborate",
        r"complete guide",
    ],
    "legal_guidance": [r"what is", r"what are", r"meaning of", r"define", r"definition", r"explain", r"tell me about"],
}

COMPLEXITY_SIGNALS = {
    "easy": [r"what is", r"define", r"tell me", r"section\s+\d+"],
    "medium": [r"difference", r"compare", r"how does", r"explain", r"procedure"],
    "hard": [r"comprehensive", r"detailed analysis", r"multi", r"discuss.*all", r"complete guide", r"elaborate"],
}

TOPIC_KEYWORDS = {
    "theft": ["theft", "steal", "stolen", "robbery", "dacoity", "snatching", "303", "304", "309", "310"],
    "hurt": ["hurt", "grievous", "injury", "assault", "poison", "acid", "114", "115", "116", "117", "118"],
    "kidnapping": ["kidnap", "abduction", "ransom", "137", "138", "139", "140"],
    "murder": ["murder", "homicide", "death", "kill", "culpable", "100", "101", "102", "103", "105"],
    "property": ["property", "trespass", "mischief", "cheating", "forgery", "329", "324", "318", "336"],
    "women": ["woman", "rape", "sexual", "dowry", "cruelty", "voyeurism", "stalking", "63", "74", "75", "80", "85"],
    "state": ["state", "treason", "sedition", "war", "president", "governor", "147", "148", "152"],
    "elections": ["election", "vote", "bribery", "personation", "169", "170", "171", "172"],
    "public_justice": ["false evidence", "perjury", "public servant", "justice", "227", "228", "248", "249"],
    "defamation": ["defamation", "libel", "slander", "reputation", "356", "357"],
    "contract": ["contract", "agreement", "breach", "consideration"],
    "cyber": ["cyber", "computer", "hack", "data", "digital", "electronic"],
}


class QueryClassifierAgent(BaseAgent):
    def __init__(self):
        super().__init__("query_classifier", "Classifies and detects query types, entities, and complexity")
        self.subscribe_to("classify_query")

    async def process(self, message: Message) -> dict:
        query = message.payload.get("query", "")
        user_id = message.payload.get("user_id")
        return self.classify(query, user_id)

    def classify(self, query: str, user_id: str | None = None) -> dict:
        query_lower = query.lower().strip()
        scores = {}
        for mode, patterns in CLASSIFIER_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, query_lower))
            if score > 0:
                scores[mode] = score

        primary_type = max(scores, key=scores.get) if scores else "legal_guidance"
        confidence = scores.get(primary_type, 1) / max(1, max(scores.values())) if scores else 0.5

        complexity = self._detect_complexity(query_lower)
        topics = self._detect_topics(query_lower)
        sections = self._extract_sections(query_lower)
        entities = self._extract_entities(query_lower)

        if user_id:
            profile = self.get_user_profile(user_id)
            profile.record_query(primary_type, topics[0] if topics else "", sections)

        self.log("classified", query=query[:60], type=primary_type, confidence=confidence, complexity=complexity)

        return {
            "primary_type": primary_type,
            "all_scores": dict(scores),
            "confidence": round(confidence, 3),
            "complexity": complexity,
            "topics": topics,
            "sections": sections,
            "entities": entities,
            "raw_query": query,
        }

    def _detect_complexity(self, query_lower: str) -> str:
        scores = {"easy": 0, "medium": 0, "hard": 0}
        for level, patterns in COMPLEXITY_SIGNALS.items():
            scores[level] = sum(1 for p in patterns if re.search(p, query_lower))
        words = len(query_lower.split())
        if words > 25:
            scores["hard"] += 1
        elif words > 12:
            scores["medium"] += 1
        else:
            scores["easy"] += 1
        return max(scores, key=scores.get)

    def _detect_topics(self, query_lower: str) -> list[str]:
        found = []
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                found.append(topic)
        return found[:3]

    def _extract_sections(self, query_lower: str) -> list[int]:
        matches = re.findall(r"(?:section|s\.|sec\.)\s*(\d+)", query_lower)
        return [int(s) for s in matches]

    def _extract_entities(self, query_lower: str) -> list[dict]:
        entities = []
        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw.isdigit() and kw in query_lower and int(kw) > 0:
                    entities.append({"type": "section", "value": int(kw)})
                    break
        # check for chapter references
        chapter_matches = re.findall(r"chapter\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)", query_lower)
        for cm in chapter_matches:
            entities.append({"type": "chapter", "value": cm})
        return entities[:10]


classifier_agent = QueryClassifierAgent()
