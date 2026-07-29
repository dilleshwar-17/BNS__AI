import json
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

KB_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "kb"


def _load_json(filename: str) -> dict:
    path = KB_DIR / filename
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("kb_load_failed", file=filename, error=str(e))
    return {}


OFFLINE_KNOWLEDGE_BASE = _load_json("offline_knowledge_base.json")
RESPONSE_TEMPLATES = _load_json("response_templates.json")


class LocalFallback:
    def query(self, query: str, mode: str = "legal_guidance") -> str:
        return query_offline_kb(query, mode)


def _find_best_match(query: str) -> dict | None:
    query_lower = query.lower()
    keywords = {
        "theft": "theft",
        "steal": "theft",
        "stolen": "theft",
        "303": "theft",
        "fir": "fir",
        "first information": "fir",
        "complaint": "fir",
        "bail": "bail",
        "release": "bail",
        "bond": "bail",
        "divorce": "divorce",
        "marriage": "divorce",
        "marital": "divorce",
        "husband": "divorce",
        "wife": "divorce",
        "consumer": "consumer_rights",
        "product": "consumer_rights",
        "defect": "consumer_rights",
        "service": "consumer_rights",
        "cyber": "cyber_crime",
        "hack": "cyber_crime",
        "online": "cyber_crime",
        "phishing": "cyber_crime",
        "1930": "cyber_crime",
        "property": "property",
        "sale deed": "property",
        "transfer": "property",
        "title": "property",
        "registration": "property",
        "constitution": "constitution",
        "fundamental": "fundamental_rights",
        "right": "fundamental_rights",
        "article 14": "fundamental_rights",
        "article 21": "fundamental_rights",
        "civil suit": "civil_procedure",
        "cpc": "civil_procedure",
        "plaint": "civil_procedure",
        "decree": "civil_procedure",
        "bnss": "criminal_procedure",
        "criminal": "criminal_procedure",
        "trial": "criminal_procedure",
        "investigation": "criminal_procedure",
        "contract": "agreements",
        "agreement": "agreements",
        "breach": "agreements",
    }
    for key, topic in keywords.items():
        if key in query_lower:
            return OFFLINE_KNOWLEDGE_BASE.get(topic)
    return None


def _build_response(entry: dict, mode: str, query: str) -> str:
    template = RESPONSE_TEMPLATES.get(mode, RESPONSE_TEMPLATES["legal_guidance"])
    context = {
        "title": entry.get("title", ""),
        "sections": entry.get("sections", ""),
        "description": entry.get("description", ""),
        "procedure": entry.get("procedure", ""),
        "citation": entry.get("citation", ""),
        "bail": entry.get("bail", ""),
        "requirements": entry.get(
            "requirements", "Varies based on specific circumstances. Consult a legal professional."
        ),
        "key_aspects": entry.get("key_aspects", "Refer to relevant legal provisions."),
        "remedies": entry.get("remedies", entry.get("procedure", "Judicial remedies available.")),
        "rights": entry.get("rights", "As per applicable law."),
        "limitation": entry.get("limitation", "As per Limitation Act, 1963."),
        "factors": entry.get("factors", "As per court discretion."),
        "reporting": entry.get("reporting", "Contact local authorities."),
        "new_features": entry.get("new_features", "As per applicable law."),
        "types": entry.get("types", "Various types exist under applicable law."),
    }
    return template.format(**context)


def query_offline_kb(query: str, mode: str = "legal_guidance") -> str:
    entry = _find_best_match(query)
    if not entry:
        return (
            "I can provide information on the following Indian legal topics:\n\n"
            "- **Theft** (BNS 303-309)\n"
            "- **FIR** (BNSS 173)\n"
            "- **Bail** (BNSS 478-483)\n"
            "- **Divorce** (HMA 1955)\n"
            "- **Consumer Rights** (CPA 2019)\n"
            "- **Cyber Crime** (IT Act 2000)\n"
            "- **Property Law** (TPA 1882)\n"
            "- **Constitution of India**\n"
            "- **Fundamental Rights**\n"
            "- **Civil Procedure** (CPC 1908)\n"
            "- **Criminal Procedure** (BNSS 2023)\n"
            "- **Agreements & Contracts** (ICA 1872)\n\n"
            "Please specify your legal question with more details."
        )
    return _build_response(entry, mode, query)
