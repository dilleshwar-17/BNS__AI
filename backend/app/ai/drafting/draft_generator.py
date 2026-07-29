from app.ai.llms.router import llm_router
from app.ai.prompts.drafting import DRAFTING_PROMPT
from app.logging import get_logger
from app.services.drafting_service import generate_draft

logger = get_logger(__name__)


FALLBACK_PHRASES = [
    "I can provide general legal information",
    "I specialize exclusively",
    "Please ask a question about",
    "This is general legal information and not legal advice",
    "I apologize, but I'm unable to process",
    "Based on relevant documents",
    "Legal knowledge graph results",
    "general legal information",
]


def _looks_like_draft(content: str) -> bool:
    c = content.strip()
    if len(c) < 100:
        return False
    for phrase in FALLBACK_PHRASES:
        if phrase in c:
            return False
    return True


class DraftGenerator:
    async def generate(self, draft_type: str, details: dict | None = None, prompt: str | None = None) -> str:
        content = generate_draft(draft_type, details)
        if details and any(v for v in details.values() if v):
            try:
                if not prompt:
                    prompt = DRAFTING_PROMPT.format(draft_type=draft_type, details=details)
                ai_content = await llm_router.route(prompt, "legal_drafting")
                if ai_content and _looks_like_draft(ai_content):
                    content = ai_content
            except Exception as e:
                logger.warning("ai_draft_failed", error=str(e))
        return content or ""
