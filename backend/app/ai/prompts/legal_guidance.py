from app.ai.prompts.prompt_registry import prompt_registry

LEGAL_GUIDANCE_PROMPT = prompt_registry.build_full_prompt("legal_guidance", "{query}", "{context}")
