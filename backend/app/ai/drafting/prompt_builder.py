import json

from app.ai.drafting.questionnaire import questionnaire
from app.core.logging import get_logger

logger = get_logger(__name__)


class DraftPromptBuilder:
    def build(self, draft_type: str, details: dict, context: str = "") -> str:
        tpl = questionnaire.get_definitions(draft_type)
        title = tpl.get("title", draft_type.replace("_", " ").title()) if tpl else draft_type.replace("_", " ").title()
        instructions = ""
        if tpl:
            instructions = tpl.get("prompt_instructions", "")
        output_structure = questionnaire.get_output_structure(draft_type)
        output_str = " → ".join(output_structure) if output_structure else "Complete legal document"

        prompt_parts = [
            "You are a legal drafting assistant for Indian law.",
            "",
            f"Draft a {title} based on the following information.",
            "",
            "INSTRUCTIONS:",
            instructions
            if instructions
            else f"Draft a professional {title} under Indian law. Use proper legal format.",
            "",
            "OUTPUT STRUCTURE:",
            output_str,
            "",
            "USER-PROVIDED DETAILS:",
            json.dumps(details, indent=2, default=str),
        ]

        if context and context.strip():
            prompt_parts.extend(
                [
                    "",
                    "LEGAL CONTEXT:",
                    context,
                ]
            )

        prompt_parts.extend(
            [
                "",
                "RULES:",
                "- Return ONLY the draft document.",
                "- Do NOT include explanations, disclaimers, or commentary.",
                "- Do NOT fabricate names, dates, locations, or evidence.",
                "- Use only the facts provided by the user.",
                "- Follow professional Indian legal drafting standards.",
                "- Use proper legal terminology and formatting.",
                "- Include signature blocks, verification, and date placeholders where applicable.",
            ]
        )

        return "\n".join(prompt_parts)
