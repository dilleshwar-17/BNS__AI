import json
import os

from app.core.logging import get_logger
from app.services.drafting_service import DRAFT_TEMPLATES
from app.services.drafting_service import get_draft_types as get_service_types

logger = get_logger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


class TemplateRegistry:
    def __init__(self):
        self._json_templates: dict[str, dict] = {}
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        if os.path.isdir(TEMPLATES_DIR):
            for fname in os.listdir(TEMPLATES_DIR):
                if fname.endswith(".json"):
                    try:
                        with open(os.path.join(TEMPLATES_DIR, fname)) as f:
                            tpl = json.load(f)
                        key = tpl.get("template", fname.replace(".json", ""))
                        self._json_templates[key] = tpl
                    except Exception as e:
                        logger.warning("template_load_failed", file=fname, error=str(e))
        self._loaded = True

    def get(self, draft_type: str) -> dict | None:
        self._ensure_loaded()
        if draft_type in self._json_templates:
            return self._json_templates[draft_type]
        svc = DRAFT_TEMPLATES.get(draft_type)
        if svc:
            return {"template": draft_type, "title": svc["title"], "template_content": svc.get("template", "")}
        return None

    def get_title(self, draft_type: str) -> str:
        tpl = self.get(draft_type)
        if tpl:
            return tpl.get("title", draft_type.replace("_", " ").title())
        return draft_type.replace("_", " ").title()

    def list_types(self) -> list[dict]:
        self._ensure_loaded()
        types = []
        for key, tpl in self._json_templates.items():
            types.append(
                {
                    "id": key,
                    "title": tpl.get("title", key),
                    "category": tpl.get("category", "general"),
                    "description": tpl.get("description", ""),
                    "estimated_time": tpl.get("estimated_time", ""),
                    "version": tpl.get("version", "1.0"),
                }
            )
        for t in get_service_types():
            if t not in self._json_templates:
                data = DRAFT_TEMPLATES.get(t, {})
                types.append(
                    {
                        "id": t,
                        "title": data.get("title", t),
                        "category": "general",
                        "description": "",
                        "estimated_time": "",
                        "version": "1.0",
                    }
                )
        return types

    def get_all_definitions(self) -> dict:
        self._ensure_loaded()
        return dict(self._json_templates)


template_registry = TemplateRegistry()
