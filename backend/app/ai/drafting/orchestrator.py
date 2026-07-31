import asyncio
from typing import AsyncIterator

from app.ai.drafting.draft_generator import DraftGenerator
from app.ai.drafting.formatter import DraftFormatter
from app.ai.drafting.prompt_builder import DraftPromptBuilder
from app.ai.drafting.questionnaire import questionnaire
from app.ai.drafting.template_registry import template_registry
from app.ai.drafting.validator import DraftValidator
from app.core.logging import get_logger

logger = get_logger(__name__)


class DraftingOrchestrator:
    def __init__(self):
        self.generator = DraftGenerator()
        self.validator = DraftValidator()
        self.formatter = DraftFormatter()
        self.prompt_builder = DraftPromptBuilder()

    async def run_pipeline(self, draft_type: str, details: dict) -> dict:
        step = "validate"
        try:
            tpl = template_registry.get(draft_type)
            if not tpl:
                return {"error": f"Unknown draft type: {draft_type}", "step": "validate"}

            logger.info("draft_pipeline_start", draft_type=draft_type, step="validate")
            errs = questionnaire.validate(draft_type, details)
            if errs:
                return {"error": "Validation failed", "validation_errors": errs, "step": "validate"}

            logger.info("draft_pipeline_retrieve", draft_type=draft_type, step="retrieve")
            legal_context = await self._retrieve_legal_context(draft_type, details)

            logger.info("draft_pipeline_prompt", draft_type=draft_type, step="build_prompt")
            prompt = self.prompt_builder.build(draft_type, details, legal_context)

            logger.info("draft_pipeline_generate", draft_type=draft_type, step="generate")
            content = await self.generator.generate(draft_type, details, prompt)

            if not content or len(content.strip()) < 50:
                from app.services.drafting_service import generate_draft as fallback_gen

                content = fallback_gen(draft_type, details) or ""

            logger.info("draft_pipeline_validate_output", draft_type=draft_type, step="validate_output")
            validation = self.validator.validate(content, draft_type, legal_context, details)

            if not validation.get("valid", True) or validation.get("hallucinated", False):
                logger.warning("ai_draft_invalid_or_hallucinated_falling_back", draft_type=draft_type, issues=validation.get("issues"))
                from app.services.drafting_service import generate_draft as fallback_gen
                content = fallback_gen(draft_type, details) or ""
                validation = self.validator.validate(content, draft_type, legal_context, details)

            logger.info("draft_pipeline_format", draft_type=draft_type, step="format")
            formatted = self.formatter.format(content, draft_type)

            return {
                "content": formatted,
                "validation": validation,
                "draft_type": draft_type,
                "title": tpl.get("title", draft_type),
                "step": "complete",
            }
        except Exception as e:
            logger.error("draft_pipeline_error", error=str(e), step=step)
            from app.services.drafting_service import generate_draft as fallback_gen

            content = fallback_gen(draft_type, details) or ""
            return {
                "content": content,
                "error": str(e),
                "draft_type": draft_type,
                "step": "error_fallback",
            }

    async def _retrieve_legal_context(self, draft_type: str, details: dict) -> str:
        try:
            retrieval_config = questionnaire.get_definitions(draft_type).get("retrieval_config", {})
            statutes = retrieval_config.get("statutes", [])
            context_parts = []
            if statutes:
                context_parts.append(f"Applicable Statutes: {', '.join(statutes)}")
            output_structure = questionnaire.get_output_structure(draft_type)
            if output_structure:
                context_parts.append(f"Output Structure: {' → '.join(output_structure)}")
            prompt_inst = questionnaire.get_prompt_instructions(draft_type)
            if prompt_inst:
                context_parts.append(f"Instructions: {prompt_inst}")

            from app.services.drafting_service import DRAFT_TEMPLATES

            svc_template = DRAFT_TEMPLATES.get(draft_type, {}).get("template", "")
            if svc_template:
                context_parts.append(f"Reference Template: {svc_template[:500]}")

            return "\n\n".join(context_parts)
        except Exception as e:
            logger.warning("legal_context_retrieval_failed", error=str(e))
            return ""

    async def stream_generate(self, draft_type: str, details: dict) -> AsyncIterator[dict]:
        steps = [
            ("validating", "Validating your inputs..."),
            ("retrieving", "Retrieving legal provisions..."),
            ("building_prompt", "Building prompt..."),
            ("generating", "Generating draft with AI..."),
            ("validating_output", "Validating generated draft..."),
            ("formatting", "Formatting document..."),
            ("complete", "Draft ready!"),
        ]
        for status, msg in steps:
            yield {
                "status": status,
                "message": msg,
                "progress": int((steps.index((status, msg)) + 1) / len(steps) * 100),
            }
            if status != "complete":
                await asyncio.sleep(0.3)

        result = await self.run_pipeline(draft_type, details)
        yield {"status": "result", "result": result, "progress": 100}


orchestrator = DraftingOrchestrator()
