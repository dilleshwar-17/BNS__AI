import os
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


class PromptRegistry:
    def __init__(self):
        self._cache = {}

    def _read_file(self, *parts: str) -> Optional[str]:
        path = os.path.join(PROMPTS_DIR, *parts)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("prompt_file_not_found", path=path)
            return None

    def get_system_prompt(self) -> str:
        parts = []
        for name in ["identity", "behavior", "safety", "formatting"]:
            content = self._read_file("system", f"{name}.md")
            if content:
                parts.append(content)
        return "\n\n".join(parts)

    def get_workflow_prompt(self, workflow: str) -> Optional[str]:
        filename = workflow.replace("_", "") + ".md"
        mapping = {
            "legal_guidance": "legal_chat",
            "legal_drafting": "legal_drafting",
            "section_lookup": "section_lookup",
            "legal_procedure": "legal_procedure",
            "rights_advisory": "rights_advisory",
            "deep_research": "deep_research",
            "document_analysis": "document_analysis",
            "case_law": "legal_chat",
            "comparison": "legal_chat",
        }
        mapped = mapping.get(workflow, "legal_chat")
        return self._read_file("workflows", f"{mapped}.md")

    def get_template(self, name: str) -> Optional[str]:
        return self._read_file("templates", name)

    def build_full_prompt(self, workflow: str, query: str, context: str = "") -> str:
        system = self.get_system_prompt()
        workflow_prompt = self.get_workflow_prompt(workflow)
        parts = [system]
        if workflow_prompt:
            parts.append(workflow_prompt)
        if context:
            parts.append(f"Retrieved Legal Context:\n{context}")
        parts.append(f"User Query:\n{query}")
        return "\n\n".join(parts)


prompt_registry = PromptRegistry()
