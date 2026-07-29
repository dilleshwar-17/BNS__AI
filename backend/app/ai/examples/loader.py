import json
import random
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

QUERIES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "BNS_queries" / "BNS_QUERIES"

QUERY_TYPE_MAP = {
    "direct": "legal_guidance",
    "definition": "section_lookup",
    "punishment": "section_lookup",
    "scenario": "legal_guidance",
    "conversational": "legal_guidance",
    "comparison": "comparison",
    "multi-section": "deep_research",
    "chapter": "legal_guidance",
    "cross-reference": "deep_research",
    "multi-hop": "deep_research",
    "long analysis": "deep_research",
    "ambiguous": "legal_guidance",
    "keyword": "legal_guidance",
    "legal advice": "legal_guidance",
    "exception": "section_lookup",
}


class FewShotLoader:
    def __init__(self):
        self._entries: list[dict] = []
        self._by_type: dict[str, list[dict]] = {}
        self._by_section: dict[int, list[dict]] = {}
        self._loaded = False

    def load(self) -> bool:
        rag_path = QUERIES_DIR / "bns_rag_dataset.jsonl"
        if not rag_path.exists():
            logger.warning("rag_dataset_not_found", path=str(rag_path))
            return False

        with open(rag_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    self._entries.append(entry)
                    mapped = QUERY_TYPE_MAP.get(entry.get("query_type", ""), "legal_guidance")
                    self._by_type.setdefault(mapped, []).append(entry)
                    for sec in entry.get("section", []):
                        self._by_section.setdefault(int(sec), []).append(entry)

        self._loaded = True
        logger.info("few_shot_loaded", entries=len(self._entries), types=len(self._by_type))
        return True

    def get_examples(
        self,
        query_type: str = "legal_guidance",
        sections: Optional[list[int]] = None,
        max_examples: int = 3,
    ) -> list[dict]:
        if not self._loaded:
            self.load()

        candidates = set()
        candidates.update(self._by_type.get(query_type, []))

        if sections:
            for sec in sections:
                candidates.update(self._by_section.get(sec, []))

        if not candidates:
            candidates.update(random.sample(self._entries, min(max_examples, len(self._entries))))

        selected = random.sample(list(candidates), min(max_examples, len(candidates)))
        return selected

    def format_examples(self, examples: list[dict]) -> str:
        parts = ["\nHere are some relevant examples to guide your response:\n"]
        for i, ex in enumerate(examples, 1):
            q = ex.get("query", "")
            a = ex.get("answer", "")
            parts.append(f"Example {i}:")
            parts.append(f"Q: {q}")
            parts.append(f"A: {a}")
            parts.append("")
        return "\n".join(parts)


_loader: Optional[FewShotLoader] = None


def get_few_shot_loader() -> FewShotLoader:
    global _loader
    if _loader is None:
        _loader = FewShotLoader()
        _loader.load()
    return _loader
