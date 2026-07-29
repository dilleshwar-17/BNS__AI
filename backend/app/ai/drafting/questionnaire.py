import re

from app.ai.drafting.template_registry import template_registry
from app.core.logging import get_logger

logger = get_logger(__name__)

VALIDATION_RULES = {
    "phone": {"pattern": r"^[+]?[\d\s\-()]{7,15}$", "message": "Enter a valid phone number"},
    "email": {"pattern": r"^[^\s@]+@[^\s@]+\.[^\s@]+$", "message": "Enter a valid email address"},
}


class Questionnaire:
    def get_definitions(self, draft_type: str) -> dict | None:
        tpl = template_registry.get(draft_type)
        if not tpl:
            return None
        if "sections" in tpl:
            return {
                "title": tpl.get("title", draft_type),
                "description": tpl.get("description", ""),
                "groups": tpl.get("sections", []),
                "conditionals": tpl.get("conditionals", []),
                "output_structure": tpl.get("output_structure", []),
                "retrieval_config": tpl.get("retrieval_config", {}),
                "prompt_instructions": tpl.get("prompt_instructions", ""),
                "export_settings": tpl.get("export_settings", {}),
            }
        from app.services.drafting_service import DRAFT_TEMPLATES

        svc = DRAFT_TEMPLATES.get(draft_type)
        if svc:
            return {"title": svc["title"], "description": "", "groups": [], "conditionals": []}
        return None

    def get_groups(self, draft_type: str) -> list:
        q = self.get_definitions(draft_type)
        return q.get("groups", []) if q else []

    def get_conditionals(self, draft_type: str) -> list:
        q = self.get_definitions(draft_type)
        return q.get("conditionals", []) if q else []

    def get_fields_flat(self, draft_type: str) -> list[dict]:
        groups = self.get_groups(draft_type)
        fields = []
        for g in groups:
            gid = g.get("id", "")
            for f in g.get("fields", []):
                f["group_id"] = gid
                fields.append(f)
        return fields

    def get_required_fields(self, draft_type: str) -> list[str]:
        return [f["key"] for f in self.get_fields_flat(draft_type) if f.get("required")]

    def get_conditional_fields(self, draft_type: str) -> list[dict]:
        return self.get_conditionals(draft_type)

    def validate(self, draft_type: str, details: dict) -> list[dict]:
        errors = []
        fields = self.get_fields_flat(draft_type)
        for field in fields:
            fid = field.get("key")
            value = details.get(fid)
            required = field.get("required", False)
            if required and (value is None or (isinstance(value, str) and not value.strip())):
                errors.append({"field": fid, "message": f"{field.get('label', fid)} is required"})
                continue
            if not value or (isinstance(value, str) and not value.strip()):
                continue
            ftype = field.get("type")
            if ftype == "number":
                try:
                    num_val = float(value) if isinstance(value, str) else value
                    v = field.get("validation", {})
                    if v.get("min") is not None and num_val < v["min"]:
                        errors.append(
                            {"field": fid, "message": f"{field.get('label', fid)} must be at least {v['min']}"}
                        )
                    if v.get("max") is not None and num_val > v["max"]:
                        errors.append(
                            {"field": fid, "message": f"{field.get('label', fid)} must be at most {v['max']}"}
                        )
                except (ValueError, TypeError):
                    errors.append({"field": fid, "message": f"{field.get('label', fid)} must be a valid number"})
            if ftype in VALIDATION_RULES and isinstance(value, str):
                rule = VALIDATION_RULES[ftype]
                if not re.match(rule["pattern"], value.strip()):
                    errors.append({"field": fid, "message": rule["message"]})
            validation = field.get("validation", {})
            if isinstance(value, str):
                if validation.get("min_length") and len(value.strip()) < validation["min_length"]:
                    errors.append(
                        {
                            "field": fid,
                            "message": f"{field.get('label', fid)} must be at least {validation['min_length']} characters",
                        }
                    )
                if validation.get("max_length") and len(value) > validation["max_length"]:
                    errors.append(
                        {
                            "field": fid,
                            "message": f"{field.get('label', fid)} must be at most {validation['max_length']} characters",
                        }
                    )
        return errors

    def validate_group(self, draft_type: str, group_id: str, details: dict) -> list[dict]:
        errors = []
        groups = self.get_groups(draft_type)
        for g in groups:
            if g.get("id") == group_id:
                for field in g.get("fields", []):
                    fid = field.get("key")
                    value = details.get(fid)
                    required = field.get("required", False)
                    if required and (value is None or (isinstance(value, str) and not value.strip())):
                        errors.append({"field": fid, "message": f"{field.get('label', fid)} is required"})
                break
        return errors

    def get_fields_for_group(self, draft_type: str, group_id: str) -> list[dict]:
        groups = self.get_groups(draft_type)
        for g in groups:
            if g.get("id") == group_id:
                return g.get("fields", [])
        return []

    def get_output_structure(self, draft_type: str) -> list[str]:
        q = self.get_definitions(draft_type)
        return q.get("output_structure", []) if q else []

    def get_prompt_instructions(self, draft_type: str) -> str:
        q = self.get_definitions(draft_type)
        return q.get("prompt_instructions", "") if q else ""


questionnaire = Questionnaire()
